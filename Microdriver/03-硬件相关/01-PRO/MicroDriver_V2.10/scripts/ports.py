"""Hierarchical port map for MicroDriver V2.10.

Derived from PRJ_MicroDriver_V2.10.pdf and the review document
《外置驱动器_PRV_MicroDriver_V2.10_现状梳理与问题清单_V1.00》.  The direction
column is written from the point of view of the *parent* (TOP) sheet:
``output`` means the child sheet drives the net.

The map is provisional: unresolved items D4/D5 in the review document
(BiSS-C NSS/MOSI usage and the lower-bridge PWM pins) may still change it.
"""

from __future__ import annotations

# sheet name -> list of (net, direction)
PORTS: dict[str, list[tuple[str, str]]] = {
    "POWER": [
        ("AD-VBUS", "output"),
    ],
    "MCU": [
        ("PWMA", "output"),
        ("PWMB", "output"),
        ("PWMC", "output"),
        ("SOA", "input"),
        ("SOB", "input"),
        ("SOC", "input"),
        ("VA", "input"),
        ("VB", "input"),
        ("VC", "input"),
        ("AD-VBUS", "input"),
        ("AD-NTC1", "input"),
        ("nSLEEP", "output"),
        ("nFAULT", "input"),
        ("CANFD-TX", "output"),
        ("CANFD-RX", "input"),
        ("RS485-TX", "output"),
        ("RS485-RX", "input"),
        ("RS485-DIR", "output"),
        ("I2C-SCL", "bidirectional"),
        ("I2C-SDA", "bidirectional"),
        ("SPI-NSS", "output"),
        ("SPI-SCK", "output"),
        ("SPI-MOSI", "output"),
        ("SPI-MISO", "input"),
        ("MA", "output"),
        ("SLO", "bidirectional"),
        ("ENCODER-A", "input"),
        ("ENCODER-B", "input"),
        ("ENCODER-Z", "input"),
    ],
    "MOTOR": [
        ("PWMA", "input"),
        ("PWMB", "input"),
        ("PWMC", "input"),
        ("SOA", "output"),
        ("SOB", "output"),
        ("SOC", "output"),
        ("VA", "output"),
        ("VB", "output"),
        ("VC", "output"),
        ("AD-NTC1", "output"),
        ("nSLEEP", "input"),
        ("nFAULT", "output"),
        ("MOTU", "output"),
        ("MOTV", "output"),
        ("MOTW", "output"),
    ],
    "communication": [
        ("CANFD-TX", "input"),
        ("CANFD-RX", "output"),
        ("RS485-TX", "input"),
        ("RS485-RX", "output"),
        ("RS485-DIR", "input"),
        ("CANH", "bidirectional"),
        ("CANL", "bidirectional"),
        ("RS485-A", "bidirectional"),
        ("RS485-B", "bidirectional"),
    ],
    "ENCODER": [
        # connector side (to J8/J9/J10 on the TOP sheet)
        ("EC-A", "input"),
        ("EC-B", "input"),
        ("EC-Z", "input"),
        ("CLK", "input"),
        ("DATA", "input"),
        ("NSS", "input"),
        ("SCK", "input"),
        ("MOSI", "input"),
        ("MISO", "output"),
        # MCU side
        ("ENCODER-A", "output"),
        ("ENCODER-B", "output"),
        ("ENCODER-Z", "output"),
        ("MA", "input"),
        ("SLO", "bidirectional"),
        ("SPI-NSS", "input"),
        ("SPI-SCK", "input"),
        ("SPI-MOSI", "input"),
        ("SPI-MISO", "output"),
    ],
}

# Sheet name -> (file stem, page number)
SHEET_FILES: dict[str, tuple[str, str]] = {
    "POWER": ("SCH_MicroDriver_V2.10_POWER", "2"),
    "MCU": ("SCH_MicroDriver_V2.10_MCU", "3"),
    "ENCODER": ("SCH_MicroDriver_V2.10_ENCODER", "4"),
    "communication": ("SCH_MicroDriver_V2.10_communication", "5"),
    "MOTOR": ("SCH_MicroDriver_V2.10_MOTOR", "6"),
}

# Sheet name -> (x, y, width, height) placement on the TOP page
SHEET_PLACEMENT: dict[str, tuple[float, float, float, float]] = {
    "POWER": (25.4, 25.4, 68.58, 55.88),
    "MCU": (104.14, 25.4, 78.74, 66.04),
    "communication": (104.14, 104.14, 78.74, 60.96),
    "MOTOR": (25.4, 93.98, 68.58, 71.12),
    "ENCODER": (193.04, 25.4, 68.58, 66.04),
}

# Net name -> list of sheet names it connects
CROSS_SHEET_NETS: dict[str, list[str]] = {}
for _sheet, _ports in PORTS.items():
    for _net, _direction in _ports:
        CROSS_SHEET_NETS.setdefault(_net, []).append(_sheet)
