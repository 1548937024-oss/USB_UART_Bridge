from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_LIBRARY = Path(
    r"D:\KiCad10.0\share\kicad\symbols\Converter_DCDC_Isolated.kicad_sym"
)
OUTPUT_LIBRARY = (
    PROJECT_ROOT
    / "hardware"
    / "USB_UART_Bridge"
    / "library"
    / "USB_UART_Bridge.kicad_sym"
)

SOURCE_SYMBOL = "CRE1S0505SC"
TARGET_SYMBOL = "IB0505LS-1WR3"


def extract_symbol_block(text: str, symbol_name: str) -> str:
    marker = f'\t(symbol "{symbol_name}"'
    start = text.index(marker)
    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise ValueError(f"Unterminated symbol block: {symbol_name}")


def main() -> None:
    source = SOURCE_LIBRARY.read_text(encoding="utf-8")
    block = extract_symbol_block(source, SOURCE_SYMBOL)
    block = block.replace(f'"{SOURCE_SYMBOL}"', f'"{TARGET_SYMBOL}"')
    block = block.replace(f"{SOURCE_SYMBOL}_", f"{TARGET_SYMBOL}_")
    block = block.replace(
        "Converter_DCDC:Converter_DCDC_Murata_CRE1xxxxxxSC_THT",
        "USB_UART_Bridge:Converter_DCDC_YLPTEC_IB0505LS-1WR3",
    )
    block = block.replace(
        "https://pim.murata.com/asset/pim4/isolatedDCDCconverter/"
        "KDC_CRE1_PDF_ISOLATEDDCDCCONVERTER",
        "https://item.szlcsc.com/6212649.html",
    )

    OUTPUT_LIBRARY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_LIBRARY.write_text(
        "(kicad_symbol_lib\n"
        "\t(version 20251024)\n"
        '\t(generator "codex")\n'
        '\t(generator_version "10.0")\n'
        f"{block}\n"
        ")\n",
        encoding="utf-8",
    )
    print(f"Generated symbol library: {OUTPUT_LIBRARY}")


if __name__ == "__main__":
    main()
