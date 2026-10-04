#!/usr/bin/env python3
"""Shared KiCad 10 schematic generation helpers for LA150C V1.00.

Ported from the MicroDriver V2.10 external-driver project so the same
reproducible workflow applies here: every object lands on the 1.27 mm grid,
symbols are embedded from a project-local library, and the geometry audit
catches junctions / shorts that ERC cannot see.

The module provides three layers:

* a small s-expression reader/writer for the KiCad 10 file format;
* a symbol-library resolver that embeds library symbols into a sheet;
* a :class:`Sheet` builder that emits a complete ``.kicad_sch``.

All schematic objects are emitted on the KiCad default 1.27 mm grid.
"""

from __future__ import annotations

import copy
import math
import uuid
from pathlib import Path

import private_parts as pp

GRID = 1.27
NAMESPACE = uuid.UUID("b41d7a52-0e3c-4c9e-8f22-5d6a1c0e77b3")

# Ground-type power symbols keep their default orientation; only supply rails
# get flipped by ``power_rotation``.
GROUND_SYMBOLS = {
    "GND",
    "GND_POWER_GROUND",
    "GNDA",
    "GNDREF",
    "PGND",
    "PGND_POWER_GROUND",
    "EGND",
    "EGND_EARTH",
    "Earth",
    "PWR_FLAG",
}


# --------------------------------------------------------------------------
# s-expression core
# --------------------------------------------------------------------------
class Q:
    """A quoted string atom."""

    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Q({self.text!r})"


Node = str | Q | list["Node"]


class Parser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.index = 0

    def parse(self) -> list[Node]:
        self._skip_space()
        if self.source[self.index] != "(":
            raise ValueError(f"Expected '(' at offset {self.index}")
        self.index += 1
        result: list[Node] = []
        while True:
            self._skip_space()
            char = self.source[self.index]
            if char == ")":
                self.index += 1
                return result
            result.append(self._parse_value())

    def _parse_value(self) -> Node:
        self._skip_space()
        if self.source[self.index] == "(":
            return self.parse()
        if self.source[self.index] == '"':
            return self._parse_string()
        start = self.index
        while (
            self.index < len(self.source)
            and not self.source[self.index].isspace()
            and self.source[self.index] not in "()"
        ):
            self.index += 1
        return self.source[start : self.index]

    def _parse_string(self) -> Q:
        self.index += 1
        value: list[str] = []
        escapes = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}
        while self.index < len(self.source):
            char = self.source[self.index]
            self.index += 1
            if char == '"':
                return Q("".join(value))
            if char == "\\" and self.index < len(self.source):
                escaped = self.source[self.index]
                self.index += 1
                value.append(escapes.get(escaped, escaped))
            else:
                value.append(char)
        raise ValueError("Unterminated quoted string")

    def _skip_space(self) -> None:
        while self.index < len(self.source) and self.source[self.index].isspace():
            self.index += 1


def atom(value: Node) -> str:
    if isinstance(value, Q):
        return value.text
    if isinstance(value, str):
        return value
    raise TypeError(f"Expected atom, got {value!r}")


def number(value: float) -> str:
    rounded = round(float(value), 4)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.4f}".rstrip("0").rstrip(".")


def quote(value: str) -> Q:
    return Q(value)


def serialize(node: Node, level: int = 0) -> str:
    if isinstance(node, Q):
        escaped = (
            node.text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    if isinstance(node, str):
        return node

    indent = "\t" * level
    if not node:
        return "()"
    if all(not isinstance(item, list) for item in node):
        return indent + "(" + " ".join(serialize(item, 0) for item in node) + ")"

    output = [indent + "(" + serialize(node[0], 0)]
    for item in node[1:]:
        if isinstance(item, list):
            output.append("\n" + serialize(item, level + 1))
        else:
            output.append(" " + serialize(item, 0))
    output.append("\n" + indent + ")")
    return "".join(output)


def direct(node: list[Node], name: str) -> list[Node] | None:
    for item in node[1:]:
        if isinstance(item, list) and item and item[0] == name:
            return item
    return None


def direct_all(node: list[Node], name: str) -> list[list[Node]]:
    return [
        item for item in node[1:] if isinstance(item, list) and item and item[0] == name
    ]


def make_uuid(kind: str, key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{key}"))


def ensure_grid(value: float, label: str) -> None:
    if abs(value / GRID - round(value / GRID)) > 1e-6:
        raise ValueError(f"{label} is off the 1.27 mm grid: {value}")


# --------------------------------------------------------------------------
# symbol libraries
# --------------------------------------------------------------------------
def read_library(path: Path) -> dict[str, list[Node]]:
    """Return ``{symbol name: definition}`` for a ``.kicad_sym`` file."""
    root = Parser(path.read_text(encoding="utf-8")).parse()
    if not root or root[0] != "kicad_symbol_lib":
        raise ValueError(f"Not a KiCad symbol library: {path}")
    result: dict[str, list[Node]] = {}
    for item in root[1:]:
        if isinstance(item, list) and item and item[0] == "symbol":
            result[atom(item[1])] = item
    return result


class Libraries:
    """Resolve ``nickname:name`` identifiers against on-disk libraries."""

    def __init__(self) -> None:
        self._paths: dict[str, Path] = {}
        self._cache: dict[str, dict[str, list[Node]]] = {}

    def register(self, nickname: str, path: Path) -> None:
        self._paths[nickname] = path

    def symbols(self, nickname: str) -> dict[str, list[Node]]:
        if nickname not in self._cache:
            path = self._paths.get(nickname)
            if path is None:
                raise KeyError(f"Unknown symbol library nickname: {nickname}")
            if not path.is_file():
                raise FileNotFoundError(f"Symbol library not found: {path}")
            self._cache[nickname] = read_library(path)
        return self._cache[nickname]

    def definition(self, lib_id: str) -> list[Node]:
        """Return a copy of a library symbol renamed to ``lib_id``."""
        if ":" not in lib_id:
            raise ValueError(f"lib_id must be 'nickname:name', got {lib_id!r}")
        nickname, name = lib_id.split(":", 1)
        source = self.symbols(nickname).get(name)
        if source is None:
            raise KeyError(f"Symbol {name!r} not found in library {nickname!r}")
        node = copy.deepcopy(source)
        node[1] = quote(lib_id)
        return node

    def pin_numbers(self, lib_id: str) -> list[str]:
        return pin_numbers(self.definition(lib_id))

    def pin_positions(self, lib_id: str) -> dict[str, tuple[float, float]]:
        return pin_positions(self.definition(lib_id))

    def pin_definitions(
        self, lib_id: str
    ) -> dict[str, tuple[float, float, float]]:
        """``{pin number: (local x, local y, angle)}`` for a library symbol."""
        return pin_definitions(self.definition(lib_id))


def pin_numbers(definition: list[Node]) -> list[str]:
    result: list[str] = []

    def walk(node: Node) -> None:
        if not isinstance(node, list):
            return
        if node and node[0] == "pin":
            number_node = direct(node, "number")
            if number_node is not None and len(number_node) >= 2:
                value = atom(number_node[1])
                if value not in result:
                    result.append(value)
        for item in node:
            if isinstance(item, list):
                walk(item)

    for item in definition[1:]:
        if isinstance(item, list):
            walk(item)
    return result


def pin_positions(definition: list[Node]) -> dict[str, tuple[float, float]]:
    result: dict[str, tuple[float, float]] = {}

    def walk(node: Node) -> None:
        if not isinstance(node, list):
            return
        if node and node[0] == "pin":
            at = direct(node, "at")
            number_node = direct(node, "number")
            if at is not None and number_node is not None and len(at) >= 3:
                result[atom(number_node[1])] = (
                    float(atom(at[1])),
                    float(atom(at[2])),
                )
        for item in node:
            if isinstance(item, list):
                walk(item)

    for item in definition[1:]:
        if isinstance(item, list):
            walk(item)
    return result


def pin_definitions(
    definition: list[Node],
) -> dict[str, tuple[float, float, float]]:
    result: dict[str, tuple[float, float, float]] = {}

    def walk(node: Node) -> None:
        if not isinstance(node, list):
            return
        if node and node[0] == "pin":
            at = direct(node, "at")
            number_node = direct(node, "number")
            if at is not None and number_node is not None and len(at) >= 3:
                angle = float(atom(at[3])) if len(at) >= 4 else 0.0
                result[atom(number_node[1])] = (
                    float(atom(at[1])),
                    float(atom(at[2])),
                    angle,
                )
        for item in node:
            if isinstance(item, list):
                walk(item)

    for item in definition[1:]:
        if isinstance(item, list):
            walk(item)
    return result


def transform_pin(
    x: float,
    y: float,
    rotation: float,
    mirror: str | None,
    local_x: float,
    local_y: float,
) -> tuple[float, float]:
    # KiCad's ``(mirror x)`` flips the symbol about its own x axis.  Combined
    # with the schematic's downward y axis this negates the local x here; the
    # sign convention was verified against a live ERC report, not derived.
    if mirror == "x":
        local_x = -local_x
    elif mirror == "y":
        local_y = -local_y
    radians = math.radians(rotation)
    rotated_x = local_x * math.cos(radians) - local_y * math.sin(radians)
    rotated_y = local_x * math.sin(radians) + local_y * math.cos(radians)
    return round(x + rotated_x, 4), round(y - rotated_y, 4)


def symbol_local_bbox(definition: list[Node]) -> tuple[float, float, float, float] | None:
    """Local bounding box of a symbol's graphics plus its pin end points."""
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Node) -> None:
        if not isinstance(node, list):
            return
        if node and node[0] in ("rectangle", "polyline", "circle"):
            for item in node:
                if isinstance(item, list) and item and item[0] in ("start", "end", "center"):
                    xs.append(float(atom(item[1])))
                    ys.append(float(atom(item[2])))
                if isinstance(item, list) and item and item[0] == "pts":
                    for point in item[1:]:
                        xs.append(float(atom(point[1])))
                        ys.append(float(atom(point[2])))
        for item in node:
            if isinstance(item, list):
                walk(item)

    walk(definition)
    for local_x, local_y in pin_positions(definition).values():
        xs.append(local_x)
        ys.append(local_y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def estimate_text_width(text: str, size: float = 1.27) -> float:
    """Rough rendered width of a text string, wide enough to space fields."""
    width = 0.0
    for char in text:
        width += size if ord(char) > 0x2000 else size * 0.72
    return width


# --------------------------------------------------------------------------
# sheet building blocks
# --------------------------------------------------------------------------
def rectangle_node(key: str, x1: float, y1: float, x2: float, y2: float) -> list[Node]:
    return [
        "rectangle",
        ["start", number(x1), number(y1)],
        ["end", number(x2), number(y2)],
        ["stroke", ["width", "0.254"], ["type", "solid"]],
        ["fill", ["type", "none"]],
        ["uuid", quote(make_uuid("rectangle", key))],
    ]


def text_node(key: str, text: str, x: float, y: float, size: float = 1.27) -> list[Node]:
    return [
        "text",
        quote(text),
        ["exclude_from_sim", "no"],
        ["at", number(x), number(y), "0"],
        ["effects", ["font", ["size", number(size), number(size)]], ["justify", "left", "bottom"]],
        ["uuid", quote(make_uuid("text", key))],
    ]


def wire_node(key: str, start: tuple[float, float], end: tuple[float, float]) -> list[Node]:
    return [
        "wire",
        ["pts", ["xy", number(start[0]), number(start[1])], ["xy", number(end[0]), number(end[1])]],
        ["stroke", ["width", "0"], ["type", "default"]],
        ["uuid", quote(make_uuid("wire", key))],
    ]


def junction_node(key: str, point: tuple[float, float]) -> list[Node]:
    return [
        "junction",
        ["at", number(point[0]), number(point[1])],
        ["diameter", "0"],
        ["color", "0", "0", "0", "0"],
        ["uuid", quote(make_uuid("junction", key))],
    ]


def auto_justify(rotation: float) -> str:
    """KiCad's automatic label justification for a given spin rotation.

    0 deg and 90 deg read left-to-right from the anchor, 180 deg and 270 deg
    read the other way, so the text justifies to the opposite side.
    """
    return "right" if int(rotation) % 360 in (180, 270) else "left"


def label_node(
    key: str, text: str, x: float, y: float, rotation: float = 0, size: float = 1.27
) -> list[Node]:
    return [
        "label",
        quote(text),
        ["at", number(x), number(y), number(rotation)],
        ["fields_autoplaced", "yes"],
        [
            "effects",
            ["font", ["size", number(size), number(size)]],
            ["justify", auto_justify(rotation), "bottom"],
        ],
        ["uuid", quote(make_uuid("label", key))],
    ]


def global_label_node(
    key: str, text: str, x: float, y: float, shape: str = "bidirectional", rotation: float = 0
) -> list[Node]:
    return [
        "global_label",
        quote(text),
        ["shape", shape],
        ["at", number(x), number(y), number(rotation)],
        ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", auto_justify(rotation)]],
        ["uuid", quote(make_uuid("global_label", key))],
    ]


def hier_label_node(
    key: str, text: str, x: float, y: float, shape: str = "input", rotation: float = 0
) -> list[Node]:
    return [
        "hierarchical_label",
        quote(text),
        ["shape", shape],
        ["at", number(x), number(y), number(rotation)],
        ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", auto_justify(rotation)]],
        ["uuid", quote(make_uuid("hier_label", key))],
    ]


def no_connect_node(key: str, x: float, y: float) -> list[Node]:
    return [
        "no_connect",
        ["at", number(x), number(y)],
        ["uuid", quote(make_uuid("no_connect", key))],
    ]


# --------------------------------------------------------------------------
# sheet builder
# --------------------------------------------------------------------------
class Sheet:
    """Emit a complete ``.kicad_sch`` file."""

    def __init__(
        self,
        path: Path,
        project: str,
        uuid_key: str,
        libraries: Libraries,
        root_uuid: str,
        sheet_uuid: str | None = None,
        page: str | None = None,
        revision: str = "V1.00",
        power_base: int = 1,
        flag_base: int = 1,
        power_rotation: float | None = None,
        paper: str = "A4",
        uuid_value: str | None = None,
        title: str = "LA150C RDIVER V1.00",
        date: str = "2026-10-04",
        company: str = "",
        comment1: str = "LA150C 集成驱动器原理图",
    ) -> None:
        self.path = path
        self.project = project
        self.uuid = uuid_value or make_uuid("sheet", uuid_key)
        self.libraries = libraries
        self.root_uuid = root_uuid
        self.sheet_uuid = sheet_uuid
        self.page = page
        self.revision = revision
        self.title = title
        self.date = date
        self.company = company
        self.comment1 = comment1
        self.power_base = power_base
        self.flag_base = flag_base
        self.power_rotation = power_rotation
        self.paper = paper
        self._definitions: dict[str, list[Node]] = {}
        self._items: list[Node] = []
        self._pwr_flag_reference = 0
        # geometry audit trail, checked in write()
        self._pins: list[tuple[str, float, float]] = []
        self._wires: list[tuple[float, float, float, float]] = []
        self._junctions: set[tuple[float, float]] = set()

    # -- properties ------------------------------------------------------
    @property
    def path_prefix(self) -> str:
        if self.sheet_uuid:
            return f"/{self.root_uuid}/{self.sheet_uuid}"
        return f"/{self.root_uuid}"

    # -- library handling ------------------------------------------------
    def embed(self, lib_id: str) -> list[Node]:
        if lib_id not in self._definitions:
            self._definitions[lib_id] = self.libraries.definition(lib_id)
        return self._definitions[lib_id]

    def pin(
        self,
        lib_id: str,
        x: float,
        y: float,
        rotation: float,
        pin_number: str,
        mirror: str | None = None,
    ) -> tuple[float, float]:
        """Actual schematic coordinate of a placed symbol's pin.

        Uses the same transform that KiCad applies, and the transform that the
        grid check uses, so wires always land exactly on the pin.
        """
        local_x, local_y = self.libraries.pin_positions(lib_id)[pin_number]
        return transform_pin(x, y, rotation, mirror, local_x, local_y)

    # -- component placement ---------------------------------------------
    def component(
        self,
        lib_id: str,
        reference: str,
        value: str,
        x: float,
        y: float,
        rotation: float = 0,
        mirror: str | None = None,
        footprint: str = "",
        description: str = "",
        value_visible: bool = True,
        dnp: bool = False,
        value_pos: tuple[float, float] | None = None,
    ) -> None:
        mapped = pp.resolve(lib_id, reference, value, description)
        if mapped is not None:
            lib_id = f"{self.project}:{mapped.symbol}"

        definition = self.embed(lib_id)
        metadata = _property_map(definition)
        if mapped is not None or lib_id.startswith(f"{self.project}:"):
            if mapped is not None:
                value = mapped.value
            footprint = metadata.get("Footprint", footprint)
            datasheet = metadata.get("Datasheet", "")
            if not description:
                description = metadata.get("Description", "")
        else:
            datasheet = ""

        pins = pin_numbers(definition)
        for pin_number, (local_x, local_y) in pin_positions(definition).items():
            pin_x, pin_y = transform_pin(x, y, rotation, mirror, local_x, local_y)
            ensure_grid(pin_x, f"{reference}.{pin_number}.x")
            ensure_grid(pin_y, f"{reference}.{pin_number}.y")
            self._pins.append((f"{reference}.{pin_number}", pin_x, pin_y))
        ensure_grid(x, f"{reference}.x")
        ensure_grid(y, f"{reference}.y")

        # Reference and Value sit side by side on one horizontal line, just
        # above the symbol's full extent (graphics + pin ends), reading
        # left-to-right.  This keeps them off the body and off the pins.
        local_box = symbol_local_bbox(definition)
        if local_box is not None:
            corners = [
                transform_pin(x, y, rotation, mirror, lx, ly)
                for lx, ly in (
                    (local_box[0], local_box[1]),
                    (local_box[2], local_box[1]),
                    (local_box[2], local_box[3]),
                    (local_box[0], local_box[3]),
                )
            ]
            left = min(corner[0] for corner in corners)
            top = min(corner[1] for corner in corners)
        else:
            left, top = x, y
        # Two stacked horizontal lines above the symbol: designator on top,
        # value underneath.  Stacking keeps dense passive rows readable even
        # when the horizontal pitch is only a few millimetres.
        ref_pos = (left, top - 1.27)
        default_val_pos = (left, top - 3.81)
        val_pos = value_pos if value_pos is not None else default_val_pos

        in_bom = "no" if reference.startswith("TP") else "yes"
        node: list[Node] = [
            "symbol",
            ["lib_id", quote(lib_id)],
            ["at", number(x), number(y), number(rotation)],
        ]
        if mirror:
            node.append(["mirror", mirror])
        node.extend(
            [
                ["unit", "1"],
                ["body_style", "1"],
                ["exclude_from_sim", "no"],
                ["in_bom", in_bom],
                ["on_board", "yes"],
                ["in_pos_files", "yes"],
                ["dnp", "yes" if dnp else "no"],
                ["uuid", quote(make_uuid("component", reference))],
                self._property(
                    "Reference",
                    reference,
                    ref_pos[0],
                    ref_pos[1],
                    # power symbols and PWR_FLAG are virtual parts (#PWR / #FLG):
                    # their reference carries no information for the reader
                    hide=reference.startswith("#"),
                ),
                self._property(
                    "Value", value, val_pos[0], val_pos[1], hide=not value_visible
                ),
                self._property("Footprint", footprint, x, y, hide=True),
                self._property("Datasheet", datasheet, x, y, hide=True),
                self._property("Description", description, x, y, hide=True),
            ]
        )
        for key in ("MPN", "LCSC Part", "Manufacturer"):
            metadata_value = metadata.get(key, "")
            if metadata_value:
                node.append(self._property(key, metadata_value, x, y, hide=True))
        if reference in pp.PENDING_PARTS:
            node.append(
                self._property(
                    "Part_Status",
                    pp.PENDING_PARTS[reference],
                    x,
                    y,
                    hide=True,
                )
            )
        for pin_number in pins:
            node.append(["pin", quote(pin_number), ["uuid", quote(make_uuid("pin", f"{reference}:{pin_number}"))]])
        node.append(
            [
                "instances",
                [
                    "project",
                    quote(self.project),
                    [
                        "path",
                        quote(self.path_prefix),
                        ["reference", quote(reference)],
                        ["unit", "1"],
                    ],
                ],
            ]
        )
        self._items.append(node)

    def power(
        self,
        lib_id: str,
        reference: str,
        x: float,
        y: float,
        rotation: float | None = None,
        value_visible: bool = True,
    ) -> None:
        """Place a power symbol; its Value (the rail name) reads to the right.

        When ``rotation`` is None the sheet-wide ``power_rotation`` is used so
        that every supply rail on a page shares one orientation.  Ground and
        flag symbols always stay at 0 deg.
        """
        if rotation is None:
            name = lib_id.split(":", 1)[-1]
            if name in GROUND_SYMBOLS:
                rotation = 0
            else:
                rotation = self.power_rotation if self.power_rotation is not None else 0
        # The rail name goes to the right of the symbol body, on the pin line,
        # so it never overlaps the graphic.  PWR_FLAG is not a rail name and
        # keeps its value hidden.
        show_value = value_visible and not lib_id.endswith("PWR_FLAG")
        self.component(
            lib_id,
            reference,
            value=_value_of(self.libraries.definition(lib_id)),
            x=x,
            y=y,
            rotation=rotation,
            value_visible=show_value,
            value_pos=(x + 2.54, y + 0.635),
        )

    def pwr_flag(self, x: float, y: float, rotation: float = 0) -> str:
        self._pwr_flag_reference += 1
        reference = f"#FLG{self.flag_base + self._pwr_flag_reference - 1:02d}"
        self.power(self.pwr_flag_lib_id, reference, x, y, rotation)
        return reference

    @property
    def pwr_flag_lib_id(self) -> str:
        return f"{self.project}:PWR_FLAG"

    # -- decoration ------------------------------------------------------
    def rectangle(self, key: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self._items.append(rectangle_node(key, x1, y1, x2, y2))

    def block(self, name: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self.rectangle(f"block:{name}", x1, y1, x2, y2)
        self.text(f"block-title:{name}", name, x1 + 2.54, y1 + 2.54, 1.5)

    def text(self, key: str, text: str, x: float, y: float, size: float = 1.27) -> None:
        self._items.append(text_node(key, text, x, y, size))

    def wire(self, x1: float, y1: float, x2: float, y2: float) -> None:
        if abs(x1 - x2) > 1e-9 and abs(y1 - y2) > 1e-9:
            raise ValueError(f"Non-orthogonal wire: ({x1},{y1}) -> ({x2},{y2})")
        if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
            raise ValueError(f"Zero-length wire at ({x1},{y1})")
        ensure_grid(x1, "wire.x1")
        ensure_grid(y1, "wire.y1")
        ensure_grid(x2, "wire.x2")
        ensure_grid(y2, "wire.y2")
        self._wires.append((x1, y1, x2, y2))
        key = f"{len(self._items)}:{(x1, y1)}:{(x2, y2)}"
        self._items.append(wire_node(key, (x1, y1), (x2, y2)))

    def junction(self, x: float, y: float) -> None:
        ensure_grid(x, "junction.x")
        ensure_grid(y, "junction.y")
        self._junctions.add((round(x, 4), round(y, 4)))
        self._items.append(junction_node(f"{len(self._items)}:{(x, y)}", (x, y)))

    def label(self, text: str, x: float, y: float, rotation: float = 0) -> None:
        ensure_grid(x, "label.x")
        ensure_grid(y, "label.y")
        self._items.append(label_node(f"{text}:{x}:{y}", text, x, y, rotation))

    def global_label(
        self, text: str, x: float, y: float, shape: str = "bidirectional", rotation: float = 0
    ) -> None:
        ensure_grid(x, "global_label.x")
        ensure_grid(y, "global_label.y")
        self._items.append(global_label_node(f"{text}:{x}:{y}", text, x, y, shape, rotation))

    def hier_label(
        self, text: str, x: float, y: float, shape: str = "input", rotation: float = 0
    ) -> None:
        ensure_grid(x, "hier_label.x")
        ensure_grid(y, "hier_label.y")
        self._items.append(hier_label_node(f"{text}:{x}:{y}", text, x, y, shape, rotation))

    def no_connect(self, x: float, y: float) -> None:
        ensure_grid(x, "no_connect.x")
        ensure_grid(y, "no_connect.y")
        self._items.append(no_connect_node(f"{x}:{y}", x, y))

    def subsheet(
        self,
        name: str,
        filename: str,
        x: float,
        y: float,
        width: float,
        height: float,
        uuid: str,
        page: str,
        pins: list[tuple[str, str, float, float, float]] | None = None,
    ) -> None:
        """Place a hierarchical sheet symbol on this (root) sheet."""
        for px, py in [(x, y), (x + width, y + height)]:
            ensure_grid(px, f"subsheet {name}.x")
            ensure_grid(py, f"subsheet {name}.y")
        node: list[Node] = [
            "sheet",
            ["at", number(x), number(y)],
            ["size", number(width), number(height)],
            ["exclude_from_sim", "no"],
            ["in_bom", "yes"],
            ["on_board", "yes"],
            ["dnp", "no"],
            ["fields_autoplaced", "yes"],
            ["stroke", ["width", "0"], ["type", "solid"], ["color", "128", "0", "0", "1"]],
            ["fill", ["color", "128", "255", "128", "1"]],
            ["uuid", quote(uuid)],
            [
                "property",
                quote("Sheetname"),
                quote(name),
                ["at", number(x), number(y - 2.54), "0"],
                ["show_name", "no"],
                ["do_not_autoplace", "no"],
                ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left", "bottom"]],
            ],
            [
                "property",
                quote("Sheetfile"),
                quote(filename),
                ["at", number(x), number(y), "0"],
                ["show_name", "no"],
                ["do_not_autoplace", "no"],
                ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left", "bottom"]],
            ],
        ]
        for index, (net, shape, px, py, rotation) in enumerate(pins or []):
            ensure_grid(px, f"{name}.{net}.x")
            ensure_grid(py, f"{name}.{net}.y")
            justify = "left" if rotation == 180 else "right"
            node.append(
                [
                    "pin",
                    quote(net),
                    shape,
                    ["at", number(px), number(py), number(rotation)],
                    ["uuid", quote(make_uuid("sheet-pin", f"{name}:{net}:{index}"))],
                    [
                        "effects",
                        ["font", ["size", "1.27", "1.27"]],
                        ["justify", justify],
                    ],
                ]
            )
        node.append(
            [
                "instances",
                [
                    "project",
                    quote(self.project),
                    [
                        "path",
                        quote(f"/{self.root_uuid}"),
                        ["page", quote(page)],
                    ],
                ],
            ]
        )
        self._items.append(node)

    # -- emit ------------------------------------------------------------
    def _property(
        self, name: str, value: str, x: float, y: float, hide: bool = False
    ) -> list[Node]:
        node: list[Node] = [
            "property",
            quote(name),
            quote(value),
            ["at", number(x), number(y), "0"],
            ["show_name", "no"],
            ["do_not_autoplace", "no"],
        ]
        if hide:
            node.append(["hide", "yes"])
        node.append(
            ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left", "bottom"]]
        )
        return node

    def to_source(self) -> str:
        title_block: list[Node] = [
            "title_block",
            ["title", quote(self.title)],
            ["date", quote(self.date)],
            ["rev", quote(self.revision)],
        ]
        if self.company:
            title_block.append(["company", quote(self.company)])
        if self.comment1:
            title_block.append(["comment", "1", quote(self.comment1)])
        root: list[Node] = [
            "kicad_sch",
            ["version", "20260306"],
            ["generator", quote("eeschema")],
            ["generator_version", quote("10.0")],
            ["uuid", quote(self.uuid)],
            ["paper", quote(self.paper)],
            title_block,
            ["lib_symbols", *self._definitions.values()],
            *self._items,
        ]
        if self.page is not None:
            root.append(["sheet_instances", ["path", quote("/"), ["page", quote(self.page)]]])
        root.append(["embedded_fonts", "no"])
        return serialize(root) + "\n"

    def audit(self) -> list[str]:
        """Geometry checks ERC cannot report.

        * a pin landing in the middle of a wire needs an explicit junction,
          otherwise KiCad silently treats it as unconnected;
        * two *component* pins sharing one coordinate is a short.  Power and
          flag symbols (ref ``#...``) are allowed to stack on a pin.
        """
        problems: list[str] = []
        rounds = {(round(x, 4), round(y, 4)) for x, y in self._junctions}
        for name, px, py in self._pins:
            if (round(px, 4), round(py, 4)) in rounds:
                continue
            for x1, y1, x2, y2 in self._wires:
                def same_part(end_x: float, end_y: float, ref: str) -> bool:
                    for other, ox, oy in self._pins:
                        if (
                            other.split(".")[0] == ref
                            and abs(ox - end_x) < 1e-6
                            and abs(oy - end_y) < 1e-6
                        ):
                            return True
                    return False

                ref = name.split(".")[0]
                starts_on_part = same_part(x1, y1, ref)
                ends_on_part = same_part(x2, y2, ref)
                if abs(x1 - x2) < 1e-9 and abs(px - x1) < 1e-6:
                    if min(y1, y2) + 1e-6 < py < max(y1, y2) - 1e-6:
                        if starts_on_part or ends_on_part:
                            problems.append(
                                f"{ref} is shorted by its own wire: {name} sits "
                                f"inside ({x1}, {y1}) -> ({x2}, {y2})"
                            )
                        else:
                            problems.append(
                                f"{name} lands mid-wire at ({px}, {py}) without a junction"
                            )
                elif abs(y1 - y2) < 1e-9 and abs(py - y1) < 1e-6:
                    if min(x1, x2) + 1e-6 < px < max(x1, x2) - 1e-6:
                        if starts_on_part or ends_on_part:
                            problems.append(
                                f"{ref} is shorted by its own wire: {name} sits "
                                f"inside ({x1}, {y1}) -> ({x2}, {y2})"
                            )
                        else:
                            problems.append(
                                f"{name} lands mid-wire at ({px}, {py}) without a junction"
                            )
        seen: dict[tuple[float, float], list[str]] = {}
        for name, px, py in self._pins:
            seen.setdefault((round(px, 4), round(py, 4)), []).append(name)
        for key, names in seen.items():
            parts = [n for n in names if not n.split(".")[0].startswith("#")]
            if len(parts) > 1:
                problems.append(f"component pins share {key}: {', '.join(parts)}")

        # A wire endpoint that lands in the middle of another wire also needs
        # an explicit junction; without it KiCad keeps the two nets apart and
        # ERC reports a stray "pin not connected".
        reported: set[tuple[float, float]] = set()
        for index, (x1, y1, x2, y2) in enumerate(self._wires):
            for other, (a1, b1, a2, b2) in enumerate(self._wires):
                if index == other:
                    continue
                for px, py in ((x1, y1), (x2, y2)):
                    key = (round(px, 4), round(py, 4))
                    if key in rounds or key in reported:
                        continue
                    on_wire = False
                    if abs(a1 - a2) < 1e-9 and abs(px - a1) < 1e-6:
                        on_wire = min(b1, b2) + 1e-6 < py < max(b1, b2) - 1e-6
                    elif abs(b1 - b2) < 1e-9 and abs(py - b1) < 1e-6:
                        on_wire = min(a1, a2) + 1e-6 < px < max(a1, a2) - 1e-6
                    if on_wire:
                        reported.add(key)
                        problems.append(
                            f"wire endpoint {key} lands mid-wire "
                            f"({a1}, {b1}) -> ({a2}, {b2}) without a junction"
                        )

        # A wire whose two endpoints are two pins of the *same* two-terminal
        # part shorts that part.  This is the mistake that keeps slipping past
        # the mid-wire check, so it gets its own explicit diagnosis.
        owners: dict[tuple[float, float], set[str]] = {}
        pin_counts: dict[str, int] = {}
        for name, px, py in self._pins:
            reference = name.split(".")[0]
            owners.setdefault((round(px, 4), round(py, 4)), set()).add(reference)
            pin_counts[reference] = pin_counts.get(reference, 0) + 1
        for x1, y1, x2, y2 in self._wires:
            a = owners.get((round(x1, 4), round(y1, 4)), set())
            b = owners.get((round(x2, 4), round(y2, 4)), set())
            shared = {
                r
                for r in (a & b)
                if not r.startswith("#") and pin_counts.get(r, 0) == 2
            }
            for ref in shared:
                problems.append(
                    f"{ref} is shorted by its own wire "
                    f"({x1}, {y1}) -> ({x2}, {y2})"
                )
        return problems

    def write(self) -> None:
        problems = self.audit()
        if problems:
            raise ValueError(
                f"{self.path.name}: geometry audit failed\n  "
                + "\n  ".join(problems)
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.to_source(), encoding="utf-8", newline="\n")


def _property_map(definition: list[Node]) -> dict[str, str]:
    result: dict[str, str] = {}
    for property_node in direct_all(definition, "property"):
        if len(property_node) >= 3:
            result[atom(property_node[1])] = atom(property_node[2])
    return result


def _value_of(definition: list[Node]) -> str:
    for property_node in direct_all(definition, "property"):
        if len(property_node) >= 3 and atom(property_node[1]) == "Value":
            return atom(property_node[2])
    return ""
