from pathlib import Path
import json
import math
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PYTHON = PROJECT_ROOT / "tools" / "python"
HARDWARE_DIR = PROJECT_ROOT / "hardware" / "USB_UART_Bridge"
PROJECT_PATH = HARDWARE_DIR / "USB_UART_Bridge.kicad_pro"
BOARD_PATH = HARDWARE_DIR / "USB_UART_Bridge.kicad_pcb"
NETLIST_PATH = PROJECT_ROOT / "generated" / "USB_UART_Bridge.net"
DESIGN_RULES_PATH = PROJECT_ROOT / "pcb_design_rules.yaml"
PROJECT_FOOTPRINT_ROOT = HARDWARE_DIR / "library"
KICAD_FOOTPRINT_ROOT = Path(r"D:\KiCad10.0\share\kicad\footprints")

os.environ["USERPROFILE"] = str(PROJECT_ROOT / ".pyhome")
os.environ["HOME"] = str(PROJECT_ROOT / ".pyhome")
os.environ.setdefault(
    "KICAD_SYMBOL_DIR",
    r"D:\KiCad10.0\share\kicad\symbols",
)

sys.path.insert(0, str(TOOLS_PYTHON))

import pcbnew
import sexpdata
import yaml


def mm(value: float) -> int:
    return pcbnew.FromMM(float(value))


def load_design() -> dict:
    with (PROJECT_ROOT / "design_intent.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_design_rules() -> dict:
    with DESIGN_RULES_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def node_values(node, tag: str) -> list:
    if not isinstance(node, list) or not node:
        return []
    return [
        child
        for child in node[1:]
        if isinstance(child, list) and child and str(child[0]) == tag
    ]


def load_netlist_connections() -> dict[str, list[tuple[str, str]]]:
    document = sexpdata.loads(NETLIST_PATH.read_text(encoding="utf-8"))
    nets = next(
        child
        for child in document[1:]
        if isinstance(child, list) and str(child[0]) == "nets"
    )
    connections: dict[str, list[tuple[str, str]]] = {}
    for net in nets[1:]:
        name_node = node_values(net, "name")
        if not name_node or name_node[0][1] is None:
            continue
        net_name = str(name_node[0][1])
        connections.setdefault(net_name, [])
        for pin_node in node_values(net, "node"):
            reference = next(
                str(child[1])
                for child in pin_node[1:]
                if isinstance(child, list) and str(child[0]) == "ref"
            )
            pin = next(
                str(child[1])
                for child in pin_node[1:]
                if isinstance(child, list) and str(child[0]) == "pin"
            )
            connections[net_name].append((reference, pin))
    return connections


def add_edge_segment(board, start, end) -> None:
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(mm(0.05))
    shape.SetStart(pcbnew.VECTOR2I_MM(*start))
    shape.SetEnd(pcbnew.VECTOR2I_MM(*end))
    board.Add(shape)


def add_edge_arc(board, start, mid, end) -> None:
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_ARC)
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(mm(0.05))
    shape.SetArcGeometry(
        pcbnew.VECTOR2I_MM(*start),
        pcbnew.VECTOR2I_MM(*mid),
        pcbnew.VECTOR2I_MM(*end),
    )
    board.Add(shape)


def add_board_outline(
    board,
    width_mm: float,
    height_mm: float,
    corner_radius_mm: float,
) -> None:
    radius = float(corner_radius_mm)
    if radius <= 0:
        add_edge_segment(board, (0.0, 0.0), (width_mm, 0.0))
        add_edge_segment(board, (width_mm, 0.0), (width_mm, height_mm))
        add_edge_segment(board, (width_mm, height_mm), (0.0, height_mm))
        add_edge_segment(board, (0.0, height_mm), (0.0, 0.0))
        return

    diagonal = radius / math.sqrt(2.0)
    add_edge_segment(board, (radius, 0.0), (width_mm - radius, 0.0))
    add_edge_arc(
        board,
        (width_mm - radius, 0.0),
        (width_mm - radius + diagonal, radius - diagonal),
        (width_mm, radius),
    )
    add_edge_segment(
        board,
        (width_mm, radius),
        (width_mm, height_mm - radius),
    )
    add_edge_arc(
        board,
        (width_mm, height_mm - radius),
        (width_mm - radius + diagonal, height_mm - radius + diagonal),
        (width_mm - radius, height_mm),
    )
    add_edge_segment(
        board,
        (width_mm - radius, height_mm),
        (radius, height_mm),
    )
    add_edge_arc(
        board,
        (radius, height_mm),
        (radius - diagonal, height_mm - radius + diagonal),
        (0.0, height_mm - radius),
    )
    add_edge_segment(board, (0.0, height_mm - radius), (0.0, radius))
    add_edge_arc(
        board,
        (0.0, radius),
        (radius - diagonal, radius - diagonal),
        (radius, 0.0),
    )


def add_rule_area(board, x1: float, y1: float, x2: float, y2: float) -> None:
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)

    layer_set = pcbnew.LSET()
    layer_set.addLayer(pcbnew.F_Cu)
    layer_set.addLayer(pcbnew.B_Cu)
    zone.SetLayerSet(layer_set)

    outline = zone.Outline()
    outline.NewOutline()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        outline.Append(mm(x), mm(y))
    board.Add(zone)


def add_board_slot(
    board,
    center_x_mm: float,
    center_y_mm: float,
    width_mm: float,
    height_mm: float,
) -> None:
    radius = float(width_mm) / 2.0
    x1 = float(center_x_mm) - radius
    x2 = float(center_x_mm) + radius
    y1 = float(center_y_mm) - float(height_mm) / 2.0
    y2 = float(center_y_mm) + float(height_mm) / 2.0

    add_edge_segment(board, (x1, y1 + radius), (x1, y2 - radius))
    add_edge_arc(
        board,
        (x1, y2 - radius),
        (float(center_x_mm), y2),
        (x2, y2 - radius),
    )
    add_edge_segment(board, (x2, y2 - radius), (x2, y1 + radius))
    add_edge_arc(
        board,
        (x2, y1 + radius),
        (float(center_x_mm), y1),
        (x1, y1 + radius),
    )


def add_isolation_slots(board, design: dict) -> None:
    for slot in design["pcb_layout"]["isolation"].get("slots", []):
        add_board_slot(
            board,
            slot["center_x_mm"],
            slot["center_y_mm"],
            slot["width_mm"],
            slot["height_mm"],
        )


def add_board_text(board, text: str, x: float, y: float, layer=pcbnew.F_SilkS) -> None:
    board_text = pcbnew.PCB_TEXT(board)
    board_text.SetText(text)
    board_text.SetLayer(layer)
    board_text.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    board_text.SetTextSize(pcbnew.VECTOR2I_MM(1.2, 1.2))
    board_text.SetTextThickness(mm(0.15))
    board.Add(board_text)


def center_board_on_page(board, design: dict) -> None:
    board_spec = design["pcb_layout"]["board"]
    if not board_spec.get("center_on_page", False):
        return

    page_width, page_height = (
        float(value) for value in board_spec["page_size_mm"]
    )
    bounds = board.GetBoardEdgesBoundingBox()
    current_center_x = pcbnew.ToMM(bounds.GetX()) + pcbnew.ToMM(bounds.GetWidth()) / 2.0
    current_center_y = pcbnew.ToMM(bounds.GetY()) + pcbnew.ToMM(bounds.GetHeight()) / 2.0
    delta_x = page_width / 2.0 - current_center_x
    delta_y = page_height / 2.0 - current_center_y
    board.Move(pcbnew.VECTOR2I(mm(delta_x), mm(delta_y)))


def load_footprint(lib_id: str):
    nickname, name = lib_id.split(":", 1)
    project_library_path = PROJECT_FOOTPRINT_ROOT / f"{nickname}.pretty"
    library_path = (
        project_library_path
        if project_library_path.exists()
        else KICAD_FOOTPRINT_ROOT / f"{nickname}.pretty"
    )
    if not library_path.exists():
        raise FileNotFoundError(f"Footprint library not found: {library_path}")
    footprint = pcbnew.FootprintLoad(str(library_path), name)
    if footprint is None:
        raise FileNotFoundError(f"Footprint not found: {lib_id}")
    return footprint


def apply_3d_model(footprint, component: dict) -> None:
    model_path = component.get("model_path")
    if not model_path:
        return
    footprint.Models().clear()
    model = pcbnew.FP_3DMODEL()
    model.m_Filename = str(model_path)
    model.m_Show = True
    offset = component.get("model_offset_mm", [0, 0, 0])
    scale = component.get("model_scale", [1, 1, 1])
    rotation = component.get("model_rotation_deg", [0, 0, 0])
    model.m_Offset = pcbnew.VECTOR3D(*offset)
    model.m_Scale = pcbnew.VECTOR3D(*scale)
    model.m_Rotation = pcbnew.VECTOR3D(*rotation)
    footprint.Add3DModel(model)


def add_nets(board, connections: dict[str, list[tuple[str, str]]]) -> None:
    for net_name in sorted(connections):
        net = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(net)


def assign_pad_nets(
    board,
    footprint,
    reference: str,
    connections: dict[str, list[tuple[str, str]]],
) -> None:
    pads_by_number = {}
    for pad in footprint.Pads():
        pads_by_number.setdefault(pad.GetNumber(), []).append(pad)

    for net_name, pins in connections.items():
        net = board.FindNet(net_name)
        if net is None:
            raise ValueError(f"Net not found on board: {net_name}")
        for connection_reference, pin_number in pins:
            if connection_reference != reference:
                continue
            pads = pads_by_number.get(pin_number, [])
            if not pads:
                raise ValueError(
                    f"Cannot find pad {reference}.{pin_number} in footprint"
                )
            for pad in pads:
                pad.SetNet(net)


def add_components(
    board,
    design: dict,
    connections: dict[str, list[tuple[str, str]]],
) -> None:
    placements = design["pcb_layout"]["placements"]
    text_settings = design["pcb_layout"].get("footprint_text", {})
    show_reference = bool(text_settings.get("show_reference", True))
    show_value = bool(text_settings.get("show_value", False))
    for reference in sorted(placements):
        component = design["components"][reference]
        spec = placements[reference]
        footprint = load_footprint(component["footprint"])
        nickname, name = component["footprint"].split(":", 1)
        footprint.SetFPID(pcbnew.LIB_ID(nickname, name))
        apply_3d_model(footprint, component)
        footprint.SetReference(reference)
        footprint.SetValue(str(component["value"]))
        footprint.SetPosition(pcbnew.VECTOR2I_MM(spec["x_mm"], spec["y_mm"]))
        footprint.SetOrientationDegrees(spec["rotation_deg"])
        footprint.Reference().SetLayer(pcbnew.F_SilkS)
        footprint.Reference().SetVisible(show_reference)
        footprint.Value().SetLayer(pcbnew.F_Fab)
        footprint.Value().SetVisible(show_value)
        board.Add(footprint)
        assign_pad_nets(board, footprint, reference, connections)


def add_mounting_holes(board, design: dict) -> None:
    holes = design["pcb_layout"]["board"]["mounting_holes"]
    library_path = KICAD_FOOTPRINT_ROOT / "MountingHole.pretty"
    for hole in holes:
        footprint = pcbnew.FootprintLoad(
            str(library_path),
            "MountingHole_2.2mm_M2",
        )
        if footprint is None:
            raise FileNotFoundError("MountingHole_2.2mm_M2")
        footprint.SetReference(hole["reference"])
        footprint.SetValue("M2")
        footprint.SetPosition(pcbnew.VECTOR2I_MM(hole["x_mm"], hole["y_mm"]))
        footprint.Reference().SetVisible(False)
        footprint.Value().SetVisible(False)
        board.Add(footprint)


def add_mounting_hole_copper_keepouts(board, design: dict) -> None:
    edge_clearance = float(
        design["pcb_layout"]["board"]["mounting_hole_copper_edge_clearance_mm"]
    )
    existing_zones = {
        zone.GetZoneName(): zone
        for zone in board.Zones()
        if zone.GetZoneName().endswith("_copper_keepout")
    }
    for hole in design["pcb_layout"]["board"]["mounting_holes"]:
        zone_name = f"{hole['reference']}_copper_keepout"
        if zone_name in existing_zones:
            board.Remove(existing_zones[zone_name])

        footprint = board.FindFootprintByReference(hole["reference"])
        if footprint is None:
            raise ValueError(
                f"Mounting hole footprint not found: {hole['reference']}"
            )
        drill_radii = []
        for pad in footprint.Pads():
            drill_size = pad.GetDrillSize()
            drill_radii.extend(
                [
                    pcbnew.ToMM(drill_size.x) / 2.0,
                    pcbnew.ToMM(drill_size.y) / 2.0,
                ]
            )
        if not drill_radii:
            raise ValueError(
                f"Mounting hole has no drill size: {hole['reference']}"
            )
        keepout_radius = max(drill_radii) + edge_clearance
        center = footprint.GetPosition()
        center_x_mm = pcbnew.ToMM(center.x)
        center_y_mm = pcbnew.ToMM(center.y)

        zone = pcbnew.ZONE(board)
        zone.SetIsRuleArea(True)
        zone.SetZoneName(zone_name)
        zone.SetDoNotAllowTracks(False)
        zone.SetDoNotAllowVias(False)
        zone.SetDoNotAllowPads(False)
        zone.SetDoNotAllowFootprints(False)
        zone.SetDoNotAllowZoneFills(True)

        layers = pcbnew.LSET()
        layers.addLayer(pcbnew.F_Cu)
        layers.addLayer(pcbnew.B_Cu)
        zone.SetLayerSet(layers)

        outline = zone.Outline()
        outline.NewOutline()
        points = 32
        for index in range(points):
            angle = 2.0 * math.pi * index / points
            x = center_x_mm + keepout_radius * math.cos(angle)
            y = center_y_mm + keepout_radius * math.sin(angle)
            outline.Append(mm(x), mm(y))
        board.Add(zone)


def add_isolation_keepouts(board, design: dict) -> None:
    barrier = design["pcb_layout"]["isolation"]["barrier_x_mm"]
    for y1, y2 in design["pcb_layout"]["isolation"]["keepout_y_mm"]:
        add_rule_area(board, barrier[0], y1, barrier[1], y2)


def apply_board_setup(board, design: dict, rules: dict) -> None:
    board_settings = design["pcb_layout"]["board"]
    limits = rules["project_design_limits"]
    board.SetCopperLayerCount(int(board_settings["copper_layers"]))

    settings = board.GetDesignSettings()
    settings.SetBoardThickness(mm(board_settings["thickness_mm"]))
    settings.m_MinClearance = mm(limits["trace_clearance_mm_min"])
    settings.m_TrackMinWidth = mm(limits["trace_width_mm_min"])
    settings.m_MinThroughDrill = mm(limits["drill_mm_min"])
    settings.m_CopperEdgeClearance = mm(limits["copper_to_edge_mm_min"])
    settings.m_HoleClearance = mm(limits["hole_clearance_mm_min"])
    settings.m_SilkClearance = mm(limits["silkscreen_clearance_mm_min"])
    settings.m_HoleToHoleMin = mm(limits["hole_to_hole_mm_min"])
    settings.m_MinGrooveWidth = mm(limits["non_plated_slot_width_mm_min"])
    settings.m_ViasMinAnnularWidth = mm(limits["via_annular_ring_mm_min"])
    settings.m_SolderMaskExpansion = mm(limits["solder_mask_expansion_mm"])
    settings.m_SolderMaskMinWidth = mm(limits["solder_mask_min_web_mm"])
    settings.m_SolderMaskToCopperClearance = mm(
        limits["solder_mask_to_copper_clearance_mm"]
    )
    settings.m_MinSilkTextHeight = mm(limits["silkscreen_text_height_mm_min"])
    settings.m_MinSilkTextThickness = mm(
        limits["silkscreen_text_thickness_mm_min"]
    )


def apply_board_netclasses(board, rules: dict) -> None:
    net_settings = board.GetDesignSettings().m_NetSettings
    default = net_settings.GetDefaultNetclass()
    configured = rules["netclasses"]
    default_fields = configured["Default"]
    default.SetClearance(mm(default_fields["clearance_mm"]))
    default.SetTrackWidth(mm(default_fields["trace_width_mm"]))
    default.SetViaDiameter(mm(default_fields["via_diameter_mm"]))
    default.SetViaDrill(mm(default_fields["via_drill_mm"]))
    default.SetDiffPairWidth(
        mm(default_fields.get("differential_width_mm", default_fields["trace_width_mm"]))
    )
    default.SetDiffPairGap(
        mm(default_fields.get("differential_gap_mm", default_fields["clearance_mm"]))
    )
    net_settings.SetDefaultNetclass(default)

    for name, fields in configured.items():
        if name == "Default":
            continue
        netclass = pcbnew.NETCLASS(name)
        netclass.SetClearance(mm(fields["clearance_mm"]))
        netclass.SetTrackWidth(mm(fields["trace_width_mm"]))
        netclass.SetViaDiameter(mm(fields["via_diameter_mm"]))
        netclass.SetViaDrill(mm(fields["via_drill_mm"]))
        netclass.SetDiffPairWidth(
            mm(fields.get("differential_width_mm", fields["trace_width_mm"]))
        )
        netclass.SetDiffPairGap(
            mm(fields.get("differential_gap_mm", fields["clearance_mm"]))
        )
        net_settings.SetNetclass(name, netclass)

    net_settings.SetNetclassPatternAssignment("*PWR_*", "Power")
    net_settings.SetNetclassPatternAssignment("GND", "Ground")
    net_settings.SetNetclassPatternAssignment("ISO_GND", "Ground")
    net_settings.SetNetclassPatternAssignment("*USB_D*", "USB")
    net_settings.SetNetclassPatternAssignment("*UART_TX*", "UART5M")
    net_settings.SetNetclassPatternAssignment("*UART_RX*", "UART5M")
    net_settings.RecomputeEffectiveNetclasses()


def update_project_netclasses(design: dict, rules: dict) -> None:
    project_data = json.loads(PROJECT_PATH.read_text(encoding="utf-8"))
    net_settings = project_data.setdefault(
        "net_settings",
        {
            "classes": [],
            "meta": {"version": 5},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [],
        },
    )
    classes = net_settings.setdefault("classes", [])
    by_name = {item.get("name"): item for item in classes}

    defaults = {}
    for name, fields in rules["netclasses"].items():
        defaults[name] = {
            "clearance": fields["clearance_mm"],
            "track_width": fields["trace_width_mm"],
            "via_diameter": fields["via_diameter_mm"],
            "via_drill": fields["via_drill_mm"],
            "diff_pair_width": fields.get(
                "differential_width_mm",
                fields["trace_width_mm"],
            ),
            "diff_pair_gap": fields.get(
                "differential_gap_mm",
                fields["clearance_mm"],
            ),
        }

    for name, fields in defaults.items():
        entry = by_name.get(name)
        if entry is None:
            entry = {
                "bus_width": 12,
                "line_style": 0,
                "microvia_diameter": 0.30,
                "microvia_drill": 0.10,
                "name": name,
                "pcb_color": "rgba(0, 0, 0, 0.000)",
                "priority": 2147483647 if name == "Default" else 0,
                "schematic_color": "rgba(0, 0, 0, 0.000)",
                "tuning_profile": "",
                "wire_width": 6,
                "diff_pair_via_gap": fields["diff_pair_gap"],
            }
            classes.append(entry)
            by_name[name] = entry
        entry.update(fields)

    net_settings["netclass_patterns"] = [
        {"netclass": "Power", "pattern": "*PWR_*"},
        {"netclass": "Ground", "pattern": "GND"},
        {"netclass": "Ground", "pattern": "ISO_GND"},
        {"netclass": "USB", "pattern": "*USB_D*"},
        {"netclass": "UART5M", "pattern": "*UART_TX*"},
        {"netclass": "UART5M", "pattern": "*UART_RX*"},
    ]

    PROJECT_PATH.write_text(
        json.dumps(project_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_project_design_rules(rules: dict) -> None:
    project_data = json.loads(PROJECT_PATH.read_text(encoding="utf-8"))
    project_board = project_data.setdefault("board", {})
    design_settings = project_board.setdefault("design_settings", {})
    design_rules = design_settings.setdefault("rules", {})
    limits = rules["project_design_limits"]
    design_rules.update(
        {
            "min_clearance": limits["trace_clearance_mm_min"],
            "min_track_width": limits["trace_width_mm_min"],
            "min_through_hole_diameter": limits["drill_mm_min"],
            "min_hole_clearance": limits["hole_clearance_mm_min"],
            "min_hole_to_hole": limits["hole_to_hole_mm_min"],
            "min_copper_edge_clearance": limits["copper_to_edge_mm_min"],
            "min_groove_width": limits["non_plated_slot_width_mm_min"],
            "min_silk_clearance": limits["silkscreen_clearance_mm_min"],
            "min_text_height": limits["silkscreen_text_height_mm_min"],
            "min_text_thickness": limits["silkscreen_text_thickness_mm_min"],
            "min_via_diameter": limits["signal_via_diameter_mm"],
            "min_via_annular_width": limits["via_annular_ring_mm_min"],
            "solder_mask_to_copper_clearance": limits[
                "solder_mask_to_copper_clearance_mm"
            ],
        }
    )
    PROJECT_PATH.write_text(
        json.dumps(project_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def validate_placement(design: dict) -> None:
    board_spec = design["pcb_layout"]["board"]
    width = board_spec["width_mm"]
    height = board_spec["height_mm"]
    overhang = design["pcb_layout"].get("allowed_edge_overhang_mm", {})
    boxes = []

    for reference, spec in design["pcb_layout"]["placements"].items():
        footprint = load_footprint(design["components"][reference]["footprint"])
        footprint.SetPosition(pcbnew.VECTOR2I_MM(spec["x_mm"], spec["y_mm"]))
        footprint.SetOrientationDegrees(spec["rotation_deg"])
        box = footprint.GetBoundingBox(False, False)
        bounds = (
            pcbnew.ToMM(box.GetX()),
            pcbnew.ToMM(box.GetY()),
            pcbnew.ToMM(box.GetX() + box.GetWidth()),
            pcbnew.ToMM(box.GetY() + box.GetHeight()),
        )
        reference_overhang = overhang.get(reference, {})
        left_limit = -float(reference_overhang.get("left", 0.0))
        top_limit = -float(reference_overhang.get("top", 0.0))
        right_limit = width + float(reference_overhang.get("right", 0.0))
        bottom_limit = height + float(reference_overhang.get("bottom", 0.0))
        if (
            bounds[0] < left_limit
            or bounds[1] < top_limit
            or bounds[2] > right_limit
            or bounds[3] > bottom_limit
        ):
            raise ValueError(
                f"{reference} exceeds board bounds: "
                f"({bounds[0]:.2f}, {bounds[1]:.2f})-"
                f"({bounds[2]:.2f}, {bounds[3]:.2f})"
            )
        boxes.append((reference, *bounds))

    for index, left in enumerate(boxes):
        for right in boxes[index + 1 :]:
            if (
                left[1] < right[3]
                and left[3] > right[1]
                and left[2] < right[4]
                and left[4] > right[2]
            ):
                raise ValueError(
                    f"Footprint bounding boxes overlap: {left[0]} and {right[0]}"
                )


def main() -> None:
    design = load_design()
    rules = load_design_rules()
    connections = load_netlist_connections()
    validate_placement(design)

    board = pcbnew.CreateEmptyBoard()
    board.SetFileName(str(BOARD_PATH))
    apply_board_setup(board, design, rules)
    apply_board_netclasses(board, rules)
    add_nets(board, connections)
    add_components(board, design, connections)
    add_mounting_holes(board, design)
    add_mounting_hole_copper_keepouts(board, design)

    board_spec = design["pcb_layout"]["board"]
    add_board_outline(
        board,
        board_spec["width_mm"],
        board_spec["height_mm"],
        board_spec["corner_radius_mm"],
    )
    add_isolation_keepouts(board, design)
    add_isolation_slots(board, design)
    add_board_text(board, "USB SIDE", 6.0, 31.0, layer=pcbnew.F_Fab)
    add_board_text(board, "ISO SIDE", 36.0, 2.0, layer=pcbnew.F_Fab)
    center_board_on_page(board, design)

    board.BuildConnectivity()
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    update_project_netclasses(design, rules)
    update_project_design_rules(rules)
    print(f"Generated PCB: {BOARD_PATH}")
    print(
        f"Placed {len(design['pcb_layout']['placements'])} footprints, "
        f"{len(design['pcb_layout']['board']['mounting_holes'])} mounting holes, "
        f"{len(design['pcb_layout']['isolation']['keepout_y_mm'])} isolation keepouts"
    )


if __name__ == "__main__":
    main()
