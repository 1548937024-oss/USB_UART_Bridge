# JLCPCB Manufacturing Review

Review date: 2026-09-19  
Reviewed by: Codex  
Status: reviewed and imported into project PCB rules

## Sources

- JLCPCB PCB capabilities: https://jlcpcb.com/capabilities/pcb-capabilities
- JLCPCB impedance service: https://jlcpcb.com/impedance
- IPC-2152: current-carrying capacity
- IPC-2221B: generic PCB design
- IPC-7351B: land pattern design

This review uses the supplier's public standard-process capability and adopts
conservative project-level values where the process minimum is too close to
the manufacturing tolerance.

## Standard Process Baseline

| Item | JLCPCB public capability | Project adopted value | Decision |
| --- | --- | --- | --- |
| Layer count | 1-32 | 2 | Standard two-layer prototype |
| Finished thickness | 0.4-4.5 mm | 1.6 mm | Standard value |
| Outer copper | 1/2/2.5/3.5/4.5 oz | 1 oz | Standard value |
| Surface finish | lead-free HASL, ENIG, OSP | lead-free HASL | Cost and prototype target |
| Minimum trace width | 0.15 mm | 0.20 mm | 33% margin |
| Minimum clearance | 0.15 mm | 0.20 mm | 33% margin |
| Minimum drill | 0.15 mm | 0.30 mm | Lower drill cost and better via yield |
| Minimum via | 0.15/0.25 mm drill/diameter | 0.30/0.60 mm | Unified signal and power via |
| Power via | not separately specified | 0.30/0.60 mm | Unified with signal via |
| PTH pad annular ring | 0.18 mm minimum | 0.20 mm board minimum; 0.25 mm design target | Component PTH pads; not the via rule |
| Copper to routed edge | 0.20 mm | 0.40 mm | Project margin |
| Copper to slot edge | 0.20 mm | 0.20 mm | Match process minimum |
| Solder mask | LPI | LPI, 0.05 mm expansion | Standard LPI process |
| Solder mask min web | supplier dimensional rule is process dependent | 0.10 mm | Conservative prototype value |
| Silkscreen clearance | 0.15 mm | 0.15 mm | Match process minimum |
| Silkscreen text height | process dependent | 0.80 mm | Readability and DFM margin |
| Silkscreen line thickness | process dependent | 0.15 mm | Match process minimum |
| NPTH slot | 1.00 mm minimum | 1.00 mm | PS1 isolation slot |
| PTH slot | 0.50 mm minimum | not used | No plated slots in design |

## Imported KiCad Rules

The following values are written to `USB_UART_Bridge.kicad_pro` and the board
design settings by `scripts/generate_pcb.py`:

| KiCad rule | Value |
| --- | --- |
| Minimum clearance | 0.20 mm |
| Minimum track width | 0.20 mm |
| Minimum through-hole diameter | 0.30 mm |
| Minimum hole clearance | 0.25 mm |
| Minimum hole-to-hole | 0.25 mm |
| Minimum copper-to-edge clearance | 0.20 mm |
| Minimum groove width | 1.00 mm |
| Minimum silkscreen clearance | 0.15 mm |
| Minimum text height | 0.80 mm |
| Minimum text thickness | 0.15 mm |
| Minimum via diameter | 0.60 mm |
| Minimum via annular width | 0.15 mm |
| Solder mask expansion | 0.05 mm |
| Solder mask minimum web | 0.10 mm |
| Solder mask to copper clearance | 0.05 mm |

Netclass widths and clearances are sourced from `pcb_design_rules.yaml`.

## Supplier Review Items

1. J1 USB-C NPTH-to-pad clearance is 0.1847 mm and is below the project
   0.25 mm hole-clearance target. It comes from the standard USB-C footprint
   geometry and requires DFM confirmation before production.
2. J2 and JP1 intentionally overhang the board edge so their bent pins remain
   accessible for Dupont wires.
3. The two-layer USB differential impedance target is 90 ohm. The default
   FR4 stack-up does not guarantee this and requires stack-up calculation,
   field solving, and first-board TDR/network-analyzer verification.
4. The PS1 STEP model is an approximate scaled model. Replace it with the
   official YLPTEC model before mechanical release.
5. The selected `0.30/0.60 mm` drill/diameter via satisfies the supplier's
   via-specific rule: the outer diameter exceeds the drill diameter by
   `0.30 mm`, above the `0.10 mm` minimum and `0.15 mm` preferred margin.
   The separate `0.18 mm` PTH annular-ring table applies to component PTH
   pads, not to this via rule. If the order form classifies the selected hole
   as non-standard, select the required plugging/tenting option.

### Via Rule Interpretation

The current JLCPCB capabilities page contains both of these statements:

- "Via diameter should be 0.1 mm (0.15 mm preferred) larger than via hole
  size."
- "PTH annular ring: 2-layer, 1 oz: recommended 0.25 mm or above; absolute
  minimum 0.18 mm." This is applied to component PTH pads.

For vias, the applicable supplier rule is the outer-diameter minus
drill-diameter requirement:

| Drill / diameter | Diameter minus drill | Result |
| --- | --- | --- |
| 0.30 / 0.40 mm | 0.10 mm | Meets relative via rule, but is not the selected project size |
| 0.30 / 0.45 mm | 0.15 mm | Meets preferred relative via rule |
| 0.30 / 0.60 mm | 0.30 mm | Meets selected project via rule with additional margin |

The project therefore keeps `0.30/0.60 mm` as the unified signal and power
via size. The PTH `0.18 mm` annular-ring value remains a separate component
pad rule.

## Approval

- Manufacturing capability review: complete.
- Project conservative values: adopted.
- KiCad board and project rule import: complete.
- Supplier DFM follow-up: required for the listed exceptions only.
