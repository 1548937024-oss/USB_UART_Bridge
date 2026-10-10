"""Hierarchical port map for LA150C RDIVER V1.00.

Power and ground nets use project power symbols (global by design); every
other cross-sheet signal is a hierarchical port.  The direction column is
written from the point of view of the parent (TOP) sheet: ``output`` means
the child sheet drives the net.
"""

from __future__ import annotations

# sheet name -> list of (net, direction)
PORTS: dict[str, list[tuple[str, str]]] = {
    "POWER": [
        ("AD_VBUS", "output"),
    ],
    "MCU": [
        ("AD_VBUS", "input"),
        ("AD_NTC", "input"),
        ("SO_A", "input"),
        ("SO_B", "input"),
        ("SO_C", "input"),
        ("PWM_A", "output"),
        ("PWM_B", "output"),
        ("PWM_C", "output"),
        ("nSLEEP", "output"),
        ("nFAULT", "input"),
        ("SPI2_SCK", "output"),
        ("SPI2_MISO", "input"),
        ("SPI2_CSN", "output"),
        ("CANFD_TX", "output"),
        ("CANFD_RX", "input"),
        ("SWDIO", "bidirectional"),
        ("SWCLK", "input"),
        ("NRST", "bidirectional"),
        ("FORCE_P", "input"),
        ("FORCE_N", "input"),
    ],
    "MOTOR": [
        ("PWM_A", "input"),
        ("PWM_B", "input"),
        ("PWM_C", "input"),
        ("nSLEEP", "input"),
        ("nFAULT", "output"),
        ("SO_A", "output"),
        ("SO_B", "output"),
        ("SO_C", "output"),
        ("AD_NTC", "output"),
        ("MOT_U", "output"),
        ("MOT_V", "output"),
        ("MOT_W", "output"),
    ],
    "ENCODER": [
        ("SPI2_SCK", "input"),
        ("SPI2_MISO", "output"),
        ("SPI2_CSN", "input"),
    ],
    "communication": [
        ("CANFD_TX", "input"),
        ("CANFD_RX", "output"),
        ("CANH", "bidirectional"),
        ("CANL", "bidirectional"),
    ],
}


# Sheet name -> (file stem, page number)
SHEET_FILES: dict[str, tuple[str, str]] = {
    "POWER": ("SCH_LA150C_POWER_V1.00", "2"),
    "MCU": ("SCH_LA150C_MCU_V1.00", "3"),
    "MOTOR": ("SCH_LA150C_DRIVER_V1.00", "4"),
    "ENCODER": ("SCH_LA150C_ENCODER_V1.00", "5"),
    "communication": ("SCH_LA150C_communication_V1.00", "6"),
}


# Sheet name -> (x, y, width, height) placement on the TOP page.
# Left blocks face MCU; MCU faces MOTOR.
SHEET_PLACEMENT: dict[str, tuple[float, float, float, float]] = {
    "POWER": (20.32, 20.32, 45.72, 33.02),
    "communication": (20.32, 63.5, 45.72, 33.02),
    "ENCODER": (20.32, 106.68, 45.72, 27.94),
    "MCU": (88.9, 20.32, 76.2, 142.24),
    "MOTOR": (187.96, 20.32, 55.88, 142.24),
}


# Net -> list of sheet names it connects (derived, kept for the audit).
CROSS_SHEET_NETS: dict[str, list[str]] = {}
for _sheet, _ports in PORTS.items():
    for _net, _direction in _ports:
        CROSS_SHEET_NETS.setdefault(_net, []).append(_sheet)
