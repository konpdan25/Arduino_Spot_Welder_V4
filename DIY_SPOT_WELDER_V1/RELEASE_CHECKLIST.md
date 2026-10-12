# Release / Validation Checklist — DIY_SPOT_WELDER_V1

A stage may only start when the previous stage is complete and recorded (date, instrument, result, photo/scope shot)
in `Reports/Validation/`. **No cell welding and no battery-connected high-current test before stage W.**

Legend: ☐ open · ☑ done (with evidence file) · ✗ failed

## Stage D — Design review (desk)

| # | Check | Status |
|---|---|---|
| D1 | KiCad 10: open project, save (format upgrade), commit | ☐ |
| D2 | KiCad 10 ERC: `kicad-cli sch erc --severity-all --output Reports/ERC/ERC_REPORT.txt KiCad/DIY_SPOT_WELDER_V1.kicad_sch` – all errors resolved or justified | ☐ |
| D3 | KiCad 10 DRC with parity: `kicad-cli pcb drc --severity-all --schematic-parity --output Reports/DRC/DRC_REPORT.txt KiCad/DIY_SPOT_WELDER_V1.kicad_pcb` | ☐ |
| D4 | OI-06/OI-07 routing finished and reviewed | ☐ |
| D5 | Inventory check OI-10 done, design.py/BOM updated | ☐ |
| D6 | Independent review of sheets 04, 05, 09 (gate path, isolation, interlocks) | ☐ |
| D7 | Netlist parity (cloud, KiCad 7 export vs design.py) | ☑ `Reports/ERC/SCHEMATIC_CONNECTIVITY_CHECK.txt` |
| D8 | Firmware host tests | ☑ `Reports/Validation/FIRMWARE_HOST_TESTS.txt` (29 tests, 0 failures) |
| D9 | Firmware compiles for ATmega328P | ☑ `Reports/Validation/FIRMWARE_AVR_BUILD.txt` |

## Stage M — Component measurements (no welding)

| # | Measurement | Acceptance | Status |
|---|---|---|---|
| M1 | RT1270 internal resistance: ΔV/ΔI with 20 A → 50 A step, 4-wire at the terminals, 100 ms | record value; compare with 32 mΩ | ☐ |
| M2 | Each IRLZ44N: RDS(on) at 10 A, V_GS 10 V (pulsed) | ≤ 25 mΩ, spread ≤ 15 % | ☐ |
| M3 | K101 contact resistance at 10 A DC, coil resistance | record | ☐ |
| M4 | K101 pick-up and drop-out voltage; operate/release time (scope) ; latching? | drop-out < 7 V; must open without coil power | ☐ |
| M5 | D101 diode test both dice; C101 polarity/ESR | — | ☐ |
| M6 | Hold-up capacitors: capacitance and ESR | ≥ 80 % nominal | ☐ |

## Stage E — Control board, energised from a current-limited lab supply (12 V, ≤ 0.5 A), power assembly NOT connected

| # | Check | Acceptance | Status |
|---|---|---|---|
| E1 | Rails at TP4–TP10 | VHOLD ≈ 11.5 V, 5V_AUX 4.8–5.2 V, 3V3 3.2–3.4 V | ☐ |
| E2 | Scope GATE_CMD/GIN during power-up, reset button, USB programming | GIN never > 0.8 V | ☐ |
| E3 | Firmware boot self-test passes; WDT reset (debug build) shows WDT RESET fault | — | ☐ |
| E4 | Hold-up: disconnect supply for 65 ms (MOSFET switch) – VDRV/VHOLD droop | VDRV > 9 V | ☐ |
| E5 | UVLO: lower VDRV with an adjustable supply on J2 pin 4 path | GIN forced low at 8.0 ± 0.3 V | ☐ |
| E6 | Reverse polarity on J1 with current-limited supply | no damage beyond F1; relay never closes | ☐ |
| E7 | NTC calibration (2 points) | ± 2 °C | ☐ |
| E8 | Foot-switch noise immunity (burst on 2 m cable, short glitches) | no trigger | ☐ |

## Stage H — Power assembly with dummy load (no cells), current-limited

Use a resistive dummy load (e.g. 0.25 Ω steel strip) so that I ≤ 50 A with a lab supply or the RT1270.

| # | Check | Acceptance | Status |
|---|---|---|---|
| H1 | Arming sequence: limiter self-test time (scope GIN) | 63–96 ms | ☐ |
| H2 | Pulse timing on scope (pre/gap/main) at 1, 10, 50 ms | ± 0.1 ms | ☐ |
| H3 | Forced firmware hang (debug build): pulse ends by U3A | ≤ 96 ms | ☐ |
| H4 | V_DS at turn-off (scope at drain bar) | < 30 V | ☐ |
| H5 | Simulated MOSFET short (bypass wire, dummy load) → STUCK_CURRENT, relay opens | relay opens < 20 ms | ☐ |
| H6 | E-STOP during READY and during a pulse | gate supply removed, relay opens | ☐ |
| H7 | MOSFET case temperatures after 20 pulses | within ± 5 K of each other (sharing) | ☐ |
| H8 | Fuse F101 type confirmed (OI-03) | — | ☐ |

## Stage W — First welds on loose nickel (no cells) — only after D, M, E, H and OI-01…OI-05 are closed

| # | Check | Status |
|---|---|---|
| W1 | Source decision documented (OI-01) | ☐ |
| W2 | Peel tests 0.15 mm Ni on Ni / on steel sample, record settings | ☐ |
| W3 | Thermal behaviour over 50 welds | ☐ |

## Stage C — Cells

Only after stage W with documented, repeatable results and a written risk acceptance by the user.

## Manufacturing release

Gerber/drill/BOM release only after stage H is complete and OI-06…OI-10 are closed.
