# DIY_SPOT_WELDER_V1

Battery spot welder for 0.15 mm nickel strip on 18650 cells: reverse engineering of the
[Arduino Spot Welder V4](https://github.com/KaeptnBalu/Arduino_Spot_Welder_V4), a new architecture,
a native KiCad project (schematic hierarchy plus a preliminary control PCB), firmware with a
non-energised test harness, and engineering documentation.

> **STATUS: PRELIMINARY — NOT VALIDATED.** Nothing has been built or measured. Do not connect
> a battery for high-current tests, and do not weld cells, based on this repository. The welding
> source (Ritar RT1270) is **not approved** (see doc 02/03), and the isolation relay is unidentified.
> Follow `RELEASE_CHECKLIST.md`.

## Summary of the engineering result

| Topic | Result |
|---|---|
| Reference V4 | Reverse engineered (doc 01). Main gaps found: no hardware pulse limit, watchdog disabled, an unfiltered foot switch can trigger a weld from a single glitch, dismissible alarms, NTC on the control board instead of the MOSFETs, stale netlist/PCB (FDB0105N407L vs IRFS7430), optional fuse. |
| Architecture | **C: MOSFET pulse switch + carry-only isolation relay + main fuse + manual disconnect + two-pole E-STOP/ARM chain** (doc 02). Using a relay as the pulse switch was rejected. |
| Source | RT1270: estimated 200–390 A, about 4× its 70 A datasheet maximum, with about 12× less weld power than a car battery. Its terminal voltage collapses to about 3 V during a weld. **Not approved** as a welding source. |
| Switch | 6× IRLZ44N (from stock), thermally limited to about 50 ms at about 300 A (estimate); STPS3045CP free-wheel diode (SPICE: V_DS peak 16 V). |
| Control | Arduino Nano + TC4422 + independent LM393 **RC pulse limiter (63–96 ms)** and **gate-drive UVLO (8 V)** + 74HCT14 input conditioning + diode-isolated hold-up banks. |
| Inventory surprises | **DFR0868 is a Beetle ESP32-C3 board, not a timer module.** IXFH20N50P3/STP6NK60 rejected (RDS(on)). TC4421 rejected (inverting). DRV887x H-bridges not needed. The relay may be a latching meter relay, which is not fail-safe. |

## Repository layout

```text
DIY_SPOT_WELDER_V1/
├── KiCad/                         KiCad project (KiCad 7 file format -> opens in KiCad 10)
│   ├── DIY_SPOT_WELDER_V1.kicad_pro / .kicad_sch (root = sheet 01) / .kicad_pcb (control PCB)
│   ├── Hierarchical_Sheets/       sheets 02 … 10
│   ├── Libraries/                 project symbol library + footprint library (self-contained)
│   ├── sym-lib-table, fp-lib-table
│   └── Generator/                 Python generator (design.py = single source of truth), checker, PCB flow
├── Firmware/
│   ├── Source/DIY_SPOT_WELDER_V1/ Arduino sketch (core, sequencer, AVR HAL, UI)
│   ├── Tests/                     host test harness (simulated plant, fault injection)
│   └── build_avr.sh               IDE-less AVR build
├── BOM/MASTER_BOM.csv             generated from design.py (generate_bom.py)
├── Calculations/                  Engineering_Models/weld_calc.py, SPICE/*.cir
├── Documentation/
│   ├── Reference_Analysis/01_REFERENCE_REVERSE_ENGINEERING.md
│   ├── Architecture/02_ARCHITECTURE_COMPARISON.md
│   ├── Electrical/03_ELECTRICAL_CALCULATIONS.md
│   ├── Safety/04_SAFETY_RISK_REGISTER.md
│   ├── Manufacturing/05_MANUFACTURING_AND_ASSEMBLY.md
│   └── Datasheets/DATASHEET_INDEX.md
├── Reports/ERC, Reports/DRC, Reports/Validation
├── README.md  DEVELOPMENT_LOG.md  OPEN_ISSUES.md  RELEASE_CHECKLIST.md
```

The prompt asked for `docs/01_…04_`. These documents live in the matching `Documentation/` subfolders, and their numbering is kept.

## Schematic hierarchy

| Sheet | Content |
|---|---|
| 01 SYSTEM_OVERVIEW | Root: block diagram, safety layers, sheet symbols |
| 02 POWER_INPUT_AND_PROTECTION | Fused tap, TVS, inrush resistor, two hold-up banks, 7805, MCP1700 |
| 03 CONTROL_AND_TIMING | Arduino Nano |
| 04 SWITCHING_AND_GATE_DRIVE | TC4422, gate clamp, J3; off-board power assembly (6× IRLZ44N, free-wheel, bus clamp, NTC) |
| 05 RELAY_CONTROL_AND_ISOLATION | Relay driver, ARM/E-STOP connector; off-board relay, fuse, disconnect, battery |
| 06 CURRENT_VOLTAGE_SENSING | Five 33k/10k dividers |
| 07 OLED_AND_USER_INTERFACE | OLED, encoder, ACK button, 74HCT14 conditioning, buzzer, LEDs |
| 08 TEMPERATURE_MONITORING | Heatsink NTC input, MCP9804 |
| 09 TRIGGER_AND_INTERLOCKS | Foot switch, ARM sense, RC pulse limiter, UVLO, wired-AND gate node |
| 10 SERVICE_AND_TEST_POINTS | 17 test points, mounting holes |

Off-board power-assembly parts are in the schematic with the *exclude from board* attribute
(`on_board no`) and a `Board = POWER_ASSEMBLY` field. **Welding current never flows on the PCB.**

## Validation (what was run, and what was not)

Executed in the cloud environment (KiCad 10 was **not** available, so KiCad 7.0.11 tools were used):

| Check | Tool | Result | Report |
|---|---|---|---|
| Schematic loads, netlist export | kicad-cli 7.0.11 | OK | `Reports/Validation/DIY_SPOT_WELDER_V1_kicad7_export.net` |
| Netlist parity vs. design intent + ERC-style rules | `KiCad/Generator/check_schematic.py` (custom, **not KiCad ERC**) | PASS, 0 errors / 0 warnings | `Reports/ERC/SCHEMATIC_CONNECTIVITY_CHECK.txt` |
| PCB DRC | pcbnew 7.0.11 `WriteDRCReport` | 0 clearance/short; **1 unconnected**; thermal-relief and silkscreen warnings | `Reports/DRC/DRC_REPORT_KiCad7.txt` |
| Firmware compile | avr-gcc 7.3.0, Arduino AVR core 1.8.6 | OK: 26.3 kB flash, 553 B static RAM | `Reports/Validation/FIRMWARE_AVR_BUILD.txt` |
| Firmware host tests | g++ with ASan/UBSan | 29 tests, 0 failures | `Reports/Validation/FIRMWARE_HOST_TESTS.txt` |
| Calculations | `weld_calc.py` | estimates | `Reports/Validation/CALCULATION_RESULTS.md` |
| SPICE | ngspice 42 (behavioural models) | free-wheel / limiter verified in simulation | `Reports/Validation/SPICE_RAW_OUTPUT.txt` |

Not executed: KiCad 10 ERC/DRC, any hardware test, thermal tests, any measurement.

### Commands for Windows 11 / KiCad 10 (run from `DIY_SPOT_WELDER_V1\`)

```bat
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch erc --severity-all --output Reports\ERC\ERC_REPORT.txt KiCad\DIY_SPOT_WELDER_V1.kicad_sch
"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb drc --severity-all --schematic-parity --output Reports\DRC\DRC_REPORT.txt KiCad\DIY_SPOT_WELDER_V1.kicad_pcb
```

Check the options with `kicad-cli sch erc --help` for your installed version. **Passing ERC/DRC does not certify physical safety.**

### Regenerating (Linux, KiCad 7.0.x)

```bash
python3 KiCad/Generator/generate_all.py      # schematic, checks, PCB placement, Freerouting, DRC
python3 BOM/generate_bom.py
python3 Calculations/Engineering_Models/weld_calc.py --md Reports/Validation/CALCULATION_RESULTS.md
make -C Firmware/Tests                       # host tests
Firmware/build_avr.sh                        # needs the Adafruit libraries (see the script)
```

Once the PCB has been edited by hand in KiCad 10, stop regenerating the PCB. Keep using `design.py` only for the
schematic, or move fully to KiCad-native editing.

### Firmware build in the Arduino IDE

Board: *Arduino Nano*, processor *ATmega328P* (Optiboot "new bootloader" is required for the watchdog).
Libraries: Adafruit SSD1306 ≥ 2.5.7, Adafruit GFX ≥ 1.11.5, Adafruit BusIO. Open `Firmware/Source/DIY_SPOT_WELDER_V1/DIY_SPOT_WELDER_V1.ino`.

## Licence and attribution

* This project is licensed under **GPL-3.0-or-later**, the same as the reference project (see the `LICENSE` file at the repository root).
* The firmware, schematic and generator scripts are new work. Concepts (double pulse, contact-triggered auto pulse,
  OLED/encoder UI) are taken from the *Arduino Spot Welder V4* by Marc Schönfleisch / Malectrics (GPL-3.0),
  credited in the source headers. The reference files in the parent repository are unmodified.
* KiCad library symbols and footprints copied into `KiCad/Libraries` come from the KiCad 7 libraries
  (CC-BY-SA 4.0 with the KiCad library exception).
