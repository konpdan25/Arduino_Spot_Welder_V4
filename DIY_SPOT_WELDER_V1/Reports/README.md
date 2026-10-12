# Reports index

| File | Content | Produced by | Notes |
|---|---|---|---|
| ERC/SCHEMATIC_CONNECTIVITY_CHECK.txt | Netlist parity + ERC-style rule checks | `KiCad/Generator/check_schematic.py` on kicad-cli 7.0.11 export | **Not KiCad ERC** (kicad-cli 7 has no `sch erc`) |
| ERC/ERC_REPORT.txt | — | to be produced with KiCad 10 (README) | not yet run |
| DRC/DRC_REPORT_KiCad7.txt | KiCad DRC of the preliminary PCB | pcbnew 7.0.11 `WriteDRCReport` | 1 unconnected item (OI-06), thermal/silk warnings |
| DRC/DRC_REPORT.txt | — | to be produced with KiCad 10 with `--schematic-parity` | not yet run |
| Validation/CALCULATION_RESULTS.md | Estimates | `weld_calc.py` | not measurements |
| Validation/SPICE_RAW_OUTPUT.txt | ngspice `.meas` results | `Calculations/SPICE/*.cir` | behavioural models |
| Validation/FIRMWARE_HOST_TESTS.txt | Host tests | `make -C Firmware/Tests` | logic only — says nothing about the power stage |
| Validation/FIRMWARE_AVR_BUILD.txt | AVR build size | `Firmware/build_avr.sh` | |
| Validation/FREEROUTING_LOG.txt | Autorouter log | `generate_all.py` | |
| Validation/DIY_SPOT_WELDER_V1_schematic.pdf | Schematic plot | kicad-cli 7 | |
| Validation/DIY_SPOT_WELDER_V1_kicad7_export.net | Netlist | kicad-cli 7 | |

No hardware test reports exist. None of these files is a safety certification.
