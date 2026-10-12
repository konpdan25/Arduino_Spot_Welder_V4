# Development Log — DIY_SPOT_WELDER_V1

## 2026-10-12 — Rev A (preliminary), branch `claude/lucid-feynman-j36xxq`

### Environment
* Claude Code cloud container, Ubuntu 24.04. KiCad 10 could not be installed (the Launchpad PPA, KiCad downloads and conda-forge KiCad were not reachable or did not exist). Ubuntu's **KiCad 7.0.11** was installed and used for netlist export, PDF/SVG plots, pcbnew scripting and DRC.
* Freerouting 1.9.0 (GitHub release) under Xvfb; ngspice 42; avr-gcc 7.3.0 + Arduino AVR core 1.8.6 (Ubuntu packages); Adafruit libraries cloned at pinned tags.
* Most manufacturer datasheet hosts were blocked, so the datasheet data come from search snippets and the KiCad libraries (see `Documentation/Datasheets/DATASHEET_INDEX.md`).

### Milestones
1. **Phase A** – reference repository audit (all files listed; firmware ZIPs extracted; KiCad 5 netlist/PCB parsed with scripts; V3 repository cloned read-only for comparison). → doc 01. Commit `4c5fd7d`.
2. **Phase B** – calculation model (`weld_calc.py`) and SPICE netlists. Findings: the RT1270 source is unsuitable, the battery terminal collapses to about 3 V, MOSFET thermal limit about 50 ms. In response, the firmware limit was reduced from 100 ms to 50 ms and the hardware limiter from about 148 ms to 63–96 ms (68 kΩ instead of 120 kΩ).
3. **Phase C** – single-source design (`design.py`), schematic generator, project libraries, netlist parity checker, PCB generator with zone placement, Freerouting, a custom SES importer (pcbnew 7's `ImportSpecctraSES` needs the GUI), GND pours and DRC. Issues fixed during the work: KiCad 7 `bold` syntax; saving a new `BOARD()` overwrote the `.kicad_pro` (net classes lost); TO-92 inline pads violated the net-class clearance, so the footprint was changed to `TO-92_Inline_Wide`; clearances relaxed to 0.2 mm at ≤ 15 V. Commit `8b6dab1`.
4. **Phase D** – firmware (core, sequencer, AVR HAL, UI) and the host harness. Issues fixed: RAM over budget (Serial pulled in by linking loose objects; strings stored in RAM). Fixes: link the core as an archive, move strings to PROGMEM. Static RAM went from 1293 B to 553 B. In the tests, the plant model was corrected to count only current-capable ON intervals (relay closed). Commit `decb746`.
5. **Phase E** – BOM generator, docs 02–05, datasheet index, open issues, release checklist, README.

### Engineering change records
| ECR | Change | Reason |
|---|---|---|
| ECR-001 | Firmware main pulse ≤ 50 ms (was 100 ms in the first draft; the reference allowed 500 ms) | MOSFET thermal estimate (doc 03 §4) |
| ECR-002 | Hardware limiter R47 120 kΩ → 68 kΩ | keep the hardware window (63–96 ms) close above the firmware limit |
| ECR-003 | Diode-isolated hold-up banks for logic/gate drive and the relay coil | RT1270 terminal collapse during a weld |
| ECR-004 | UVLO threshold 8.0 V (divider 22k/10k) | IRLZ44N enhancement margin; 7805 headroom |
| ECR-005 | GIN pull-down 47k → 22k | margin against TC4422 input leakage |
| ECR-006 | TO-92 footprints → TO-92_Inline_Wide | DRC clearance and hand soldering |
| ECR-007 | ADC reference kept at AVCC (an internal 1.1 V option was dropped) | the AREF settling time conflicts with continuous supervision |
