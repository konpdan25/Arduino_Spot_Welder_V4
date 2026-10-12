# 01 — Reference Design Reverse Engineering (Arduino Spot Welder V4 / V3)

| Item | Value |
|---|---|
| Document | DIY_SPOT_WELDER_V1 / 01_REFERENCE_REVERSE_ENGINEERING |
| Revision | A (2026-10-12) |
| Reference | https://github.com/KaeptnBalu/Arduino_Spot_Welder_V4 (this repository, commit `bedeb67`) and https://github.com/KaeptnBalu/Arduino_Spot_Welder_V3 (shallow clone, default branch) |
| Licence of reference | GPL-3.0 (`LICENSE` at repository root). Firmware headers: "Copyright(c)2024 Marc Schönfleisch", GPL-3.0-or-later. |
| Method | Every file in the repository was listed; firmware ZIPs were extracted and read; the KiCad 5 netlist and the PCB were parsed with scripts (KiCad 7.0.11 `pcbnew` Python API). No hardware was measured. |

Legend used throughout: **[EVIDENCE]** = read directly from a file, **[CALC]** = derived by calculation,
**[ASSUMPTION]**, **[UNKNOWN]**.

---

## 1. Repository audit

### 1.1 File inventory

| Path | Content | Readable? | Notes |
|---|---|---|---|
| `README.md` | Feature description, V4 changes | yes | States 12 V car battery, "Maximum 800A total" |
| `LICENSE` | GPL-3.0 text | yes | |
| `Arduino_Code/V4.0.{1,2,3}_Arduino_Code/*.zip` | Firmware, 3 versions | yes (extracted) | Each ZIP: `.ino` (~1500 lines), `.h` (~365 lines), `printf.h` |
| `KiCAD_PCB_Files/KiCAD_Project/Arduino_Spot_Welder.sch` | KiCad 4/5 legacy schematic (EESchema v2) | yes | Title "Arduino Spot Welder V4", Rev 4.0 |
| `…/Arduino_Spot_Welder.bak` | Previous schematic | yes | Title "V3.2"; only title/rev differ from `.sch` |
| `…/Arduino_Spot_Welder.net` | Netlist | yes | Generated 24/09/2020, tool "Eeschema 4.0.4", title "V3.2" — **stale** (see 1.3) |
| `…/Arduino_Spot_Welder.kicad_pcb` | Two-board PCB in one file | yes (KiCad 7 loads it) | 2 copper layers, 1.6 mm |
| `…/Arduino_Spot_Welder-cache.lib` | Symbol cache | yes | Only source of the custom symbols |
| `…/fp-lib-table` | Footprint libraries | yes | Absolute paths `E:\Cloud\SkyDrive\Own_Kicad_Libraries\…` — **libraries not in repo** |
| `KiCAD_PCB_Files/Gerber/{Arduino,Mosfet}_PCB_V4/*` | Gerbers + drill | yes (not rendered) | Mosfet board: README demands **4 oz copper** |
| `KiCAD_PCB_Files/Spot_Welder_V4_Schematic.pdf`, `…Layout.JPG` | Prints | not parsed | |
| `Parts/BOM_Arduino_Spot_Welder_V4.xlsx` | BOM | yes (XML parsed) | Matches `Parts/README.md` |
| `Parts/Aluminum_Parts/*` | 90×15×4 mm aluminium bars (DXF/PDF) | partially | Current-carrying bars bolted to the MOSFET board |
| `Parts/Spot_Welder_V4_Case/*` | Fusion 360 / STEP / STL case | not parsed | Case includes 30 mm 12 V fan and ANL 300 A fuse mount |

### 1.2 Missing / non-reproducible items

* Custom footprint libraries (`pots_own`, `Rotary-Encoders`, `OLED_SSD1306`, `arduino`, `TO-263_Schematic`) are referenced by absolute Windows paths and are **not in the repository**. The PCB file embeds the footprints, so the board opens, but the schematic→PCB flow cannot be reproduced without them.
* No simulation files, no test reports, no measurement data, no mechanical drawing of the busbar/cable stack, no fuse selection calculation.

### 1.3 Inconsistencies found between files [EVIDENCE]

| # | Finding | Files |
|---|---|---|
| I-1 | MOSFET value is `IRFS7430TRL7PP` in the schematic and BOM but `FDB0105N407L` in the netlist and on the PCB footprints `T1…T6`. The netlist/PCB were not regenerated after the part change. | `.sch` lines 730–786 vs `.net`, `.kicad_pcb` |
| I-2 | Netlist title block says "Arduino Spot Welder V3.2". | `.net` |
| I-3 | Firmware uses `OLED_RESET = 4` and `PIN_LED = 4` (same pin D4). D4 is not routed on the PCB, so harmless, but the library will toggle it. | `Arduino_Spot_Welder_V4_0_3.h` |
| I-4 | Menu "Weld Pulse Sound" shows the **auto-pulse** flag instead of the sound flag. | `.ino` line 509 (`pData.pFlags.en_autoPulse ? LS_SOUNDON …`) |
| I-5 | V4.0.3 removed the battery calibration menu, but `batteryOffset` is still added to the pulse voltage (not to the idle voltage). | `.ino` `checkForPulseDataEvent()` |
| I-6 | Comment "PIN_TEMP … Buzzer output" (copy/paste). | `.h` |

---

## 2. Architecture of the reference

```
 12 V lead-acid (car, 40–60 Ah, 440–600 A CCA)          ANL 300 A fuse (OPTIONAL in BOM)
   (+)───────────────[16 mm² cable]──────────────── (+) electrode
   (+)──P1 terminal──D1 Schottky──VCC──┬─ Arduino Nano VIN (on-board 5 V reg.)
                                       ├─ MCP1407 VDD (gate driver)
                                       └─ C3,C4 470 µF + C1 10 nF + C2 1 µF, TVS1 SMAJ13A
   Nano D5 ──(R1 10k pull-down)──► MCP1407 IN ──OUT──► TVS2 SMAJ13A clamp ──► 6× R 30 Ω ──► 6× gate
   (−) electrode ──[cable]── Probe / drain bar ──► 6× IRFS7430 (D²PAK-7) ──► battery_minus bar ──[cable]── (−)
                     │                                      3× SLD8S14A TVS drain–source
                     └─ P7/P5 "AutoPulse" → R9 1k to GND, R10 620 Ω → D3 4.3 V zener + BAV99 → D3 (Nano)
   battery_minus bar ──P6/P4 "GND_con"──► control GND (second ground connection besides P1)
   Nano: A0 = battery divider 10k/3k3 (+12V before D1), A1 = buzzer (Q1), A3 = NTC divider,
         D2/D8/D6 = encoder A/B/SW, D7 = foot switch (internal pull-up), I²C A4/A5 = SSD1306 OLED
```

Physical construction [EVIDENCE: PCB parse, `Parts/`]: two PCBs in one `.kicad_pcb` (control board ≈ 47 × 77 mm,
MOSFET board ≈ 39 × 77 mm), stacked with M3×20 screws. The MOSFET board carries `/Probe` (drain) and
`/battery_minus` (source) copper zones on F.Cu (each ≈ 20 × 70 mm) plus two 90 × 15 × 4 mm aluminium bars
bolted on top as the main conductors; welding cables are bolted to the bars. TVS3–5 and the six 30 Ω
gate resistors are on B.Cu.

---

## 3. Circuit block analysis

### 3.1 Power input (control supply)

| Aspect | Reference implementation [EVIDENCE] |
|---|---|
| Source | Battery +12 V via 2-pole 3.5 mm terminal block P1 (thin wires) |
| Reverse polarity | D1 CDBA160 (60 V, 1 A Schottky) — protects **control electronics only** |
| Transient | TVS1 SMAJ13A (13 V standoff, 400 W) on VCC |
| Bulk / hold-up | C3, C4 2×470 µF/25 V (added in V4 because the Nano rebooted on long pulses in V3) |
| 5 V rail | Nano on-board regulator from VIN |

[CALC] Hold-up with 940 µF and ≈60 mA load: ΔV/Δt ≈ 64 V/s → 100 ms pulse costs ≈6.4 V. With a car battery
the terminal sag is small, so this was adequate for the intended source. **With a 7 Ah battery the
terminal collapses to a few volts during a weld (see doc 03), so this scheme would not hold the
control and gate-drive rails.**

Failure modes: D1 short → reverse-polarity damage; TVS1 short (after a large transient) → fuse-less
supply tap overheats (no fuse on P1); P1 wire not fused at the battery.

### 3.2 Gate drive

| Aspect | Value [EVIDENCE] |
|---|---|
| Driver | P2 = MCP1407-E/SN, SOIC-8, non-inverting, 6 A peak, VDD = VCC (≈12 V) |
| Pinout used | 1,8 VDD; 2 IN; 3 NC; 4,5 GND; 6,7 OUT — consistent with the MCP1407 datasheet |
| Default-off | R1 10 kΩ IN→GND: input low when the Nano is in reset (pins hi-Z) ✔ |
| Gate clamp | TVS2 SMAJ13A on the common gate bus (V3.2 moved it from per-gate to one on the control board) |
| Gate resistors | R13–R18, 30 Ω, 1206, one per MOSFET, on the MOSFET board |
| Inter-board | 1×6 header pairs, all pins in parallel (V3.3 note: paralleled pins to fix contact problems) |

[CALC] With 30 Ω per gate and ≈12 V drive the per-gate peak current is ≈0.4 A; IRFS7430 Qg ≈300 nC
(typical, datasheet value not re-verified here) → ≈1 µs switching edges. Slow edges increase
switching loss but limit di/dt and therefore the inductive overshoot — a deliberate trade-off.

Failure modes: gate driver VDD follows the battery; if the battery sags far, the gates are under-driven
and the MOSFETs enter linear mode (high dissipation). No UVLO exists.

### 3.3 Switching stage

| Aspect | Value |
|---|---|
| Devices | 6× IRFS7430TRL7PP (40 V, D²PAK-7) per schematic/BOM; footprint labelled FDB0105N407L |
| Topology | Low-side switch, drains = negative electrode ("Probe"), sources = battery − |
| Clamping | 3× SLD8S14A (Littelfuse, 14 V standoff, BOM lists "7 kW") drain–source |
| Free-wheel | **None** — the cable inductance energy is dissipated in the TVS / MOSFET avalanche at every turn-off |
| Conductors | 4 oz copper zones + 2 aluminium bars (90×15×4 mm, ≈60 mm² each) |
| Claimed rating | README: "Maximum 800A total" |

Failure modes: (1) MOSFETs fail short → current is limited only by battery + cables; with a car battery
this is >1 kA and the only protection is the **optional** ANL fuse. (2) TVS degradation. (3) Solder
joints of D²PAK under thermal cycling. (4) No reverse-polarity protection of the power path: a
reversed battery forward-biases all body diodes, so touching the electrodes to the workpiece produces an
uncontrolled current.

### 3.4 Auto-pulse (probe contact) sense

P7 (MOSFET board) = drain node → P5 (control board) → R9 1 kΩ to GND and R10 620 Ω → D3 4.3 V zener + D2 BAV99
clamp → Nano D3. When both tips touch the nickel, the drain is pulled to battery + through the workpiece;
R9 loads the node (≈12 mA). [CALC] Zener current ≈ (12 − 4.3)/620 ≈ 12 mA, R10 dissipation ≈ 96 mW
(0805, ok). Works as a contact detector; also usable as a drain-voltage indicator.

### 3.5 Battery voltage measurement

A0 = +12 V (before D1, since V3.2) × 3k3/(10k+3k3) → scale 4.03 (firmware constant), C7 10 nF, D4 BAV99
clamp. Resolution ≈ 20 mV/LSB. Accuracy depends on the Nano's 5 V (used as ADC reference). Sampled every
20 s in idle and once at the end of each pulse.

### 3.6 Temperature

NTC1 (Murata NCP21XV103J03RA, 10 kΩ, 0805) with R7 10 kΩ pull-up to A3. **PCB position: x = 93.5, y = 68.0 mm,
on the control board under the Nano** [EVIDENCE: PCB parse]. It measures control-board / case air
temperature, not the MOSFETs. Firmware alarm at 65 °C, sampled every 10 s.

### 3.7 User interface

SSD1306 128×64 I²C OLED (pin order GND-VCC-SCL-SDA per BOM note), Bourns PEC11L encoder with RC filters
(R2–R5 10k, C5–C6 10 nF), piezo buzzer via Q1 MMBT3904 (R6 1k base, R8 1k bleed), foot switch on D7 with
**internal pull-up only, no RC filter, no ESD protection**.

### 3.8 Grounding

Control GND is connected both through P1 (battery − wire) and through P4/P6 (to the MOSFET source bar).
[ASSUMPTION: build guide not reachable from this environment] If the P1 negative wire goes to the battery
post and the source bar goes to the battery post through the welding cable, the thin control ground is
in parallel with the welding-current return; the voltage drop on the heavy cable then drives current
through the control ground. A single-point ground at the source bar is preferable (adopted in our design).

---

## 4. Firmware analysis (V4.0.3, `Arduino_Spot_Welder_V4_0_3.ino`)

| Topic | Finding [EVIDENCE] | Risk |
|---|---|---|
| Startup | `reset_mcusr()` in `.init3` clears MCUSR and **disables the watchdog**; `setup()` sets D5 as OUTPUT (default LOW) | Reset cause discarded; no WDT |
| Watchdog | Not used anywhere. "Reboot" asks the user to remove power. | Firmware lock-up is not detected. Lock-up with D5 HIGH ⇒ sustained current; only the optional fuse limits it. |
| Pulse generation | `sendWeldPulse()`: `weldPulse(ON); delay(pre); OFF; delay(pre); ON; delay(main); analogRead(A0); OFF` | `delay()` = 1 ms granularity, interrupts enabled (Timer0, encoder ISR, `tone()` on Timer2). Main pulse is lengthened by one ADC conversion (≈110 µs). |
| Pre-pulse | `pre = main × shortPulseTime/100`, min 1 ms; skipped if `main ≤ 3 ms`; gap = pre | Integer math (uint16×uint8 → unsigned int) does not overflow for 500 × 100 |
| Pulse limits | 1 … `maxPulseTime` (default 100, settable up to 500 ms) | No hardware limit |
| Foot-switch trigger | `else if (!digitalRead(PIN_FOOT_SWITCH)) sendWeldPulse(…, FS_TRIGGER_DELAY=200 …)`, then `delay(200)` and the pulse fires **without re-checking the switch** | **A single noise glitch read LOW on the (unfiltered) foot-switch line triggers a weld 200 ms later.** |
| Auto-pulse trigger | Contact must persist through the delay; else aborted | Adequate |
| Re-trigger | Waits for release (max 2 s) then 500 ms lock-out | Adequate |
| Low/high battery | Checked every 20 s; event sets an alarm screen; **a button click returns to the main screen and welding is possible until the next 20 s check** | Alarm is advisory, not an interlock |
| Over-temperature | Same pattern, every 10 s, alarm dismissable | Advisory only |
| Standby | After 5 min inactivity both triggers disabled | Good |
| Boot with foot switch closed | `FootSwitch_Alarm()` infinite loop with buzzer, output low | Safe |
| `LowBattery_Sound()` | Busy loop until button pressed | Blocks UI (safe w.r.t. welding) |
| I²C clock | `Adafruit_SSD1306 display(…, 800000L)` — 800 kHz exceeds ATmega328P TWI and SSD1306 400 kHz specs | Display glitches/hang possible |
| Current display | `PulseAmps = V × 117` (fixed 8.5 mΩ assumption) | Not a measurement |
| Output during reset/boot | ATmega pins are hi-Z during reset/bootloader; R1 keeps IN low ✔. ISP programming toggles D11–D13 only ✔ | Safe |

---

## 5. Protection review summary

| Protection | Present? | Comment |
|---|---|---|
| Main fuse | Optional (ANL 300 A) | Not part of the core BOM; should be mandatory |
| Control-supply fuse | No | |
| Reverse polarity — control | Yes (D1) | |
| Reverse polarity — power stage | **No** | Body diodes conduct |
| Undervoltage lock-out (gate drive) | **No** | |
| Hardware pulse-length limit | **No** | MCU is the only means of ending a pulse |
| Watchdog | **No** (explicitly disabled) | |
| Over-temperature | Firmware, air temperature, dismissable | |
| Inductive clamp | TVS ×3 (V3: 4× 5 kW) | Energy absorbed every pulse; no free-wheel diode |
| Gate clamp | SMAJ13A | Good |
| Default-off gate | 10 k pull-down | Good |
| Emergency isolation | None (only battery clamps / fuse) | |
| Trigger debouncing | Foot switch: none | See §4 |

---

## 6. Lessons applied to DIY_SPOT_WELDER_V1

1. **Hardware must end a pulse on its own.** Add an RC/comparator pulse-length limiter and a gate-drive
   UVLO acting on the driver input, independent of the MCU (implemented, sheet 04/09).
2. **Default-off by hardware**: keep the driver-input pull-down; choose a non-inverting driver (TC4422);
   per-gate pull-downs on the power assembly.
3. **The control/gate rail must not follow a collapsing battery**: diode-isolated hold-up bank sized for
   the longest pulse (critical for a 7 Ah battery).
4. **Mandatory main fuse + manual disconnect** in the battery positive, sized from the actual source.
5. **Free-wheel diode across the load** instead of relying only on avalanche/TVS energy absorption.
6. **Trigger hygiene**: Schmitt-trigger input with RC filter and firmware re-confirmation of the trigger
   throughout the delay.
7. **Interlocks are latched faults, not dismissable screens.** Low voltage, over-temperature and
   hardware-limit events block welding until the cause is gone *and* the user acknowledges.
8. **Watchdog enabled**, reset cause recorded (WDRF/BORF) and shown as a fault.
9. **Temperature sensor on the MOSFET heatsink**, not on the control board.
10. **Single-point ground** at the MOSFET source bar.
11. **Keep schematic, netlist, PCB and BOM generated from one source** (our generator script + project libraries in the repo).
12. Don't reuse the reference's 800 A / car-battery assumptions: our source is a 7 Ah VRLA battery with a
    completely different source impedance (doc 03).

## 7. GPL-3.0 obligations

* Our firmware is newly written (no code copied). It re-implements concepts (double pulse, auto-pulse contact
  detection) which are not copyrightable as such. We nevertheless publish it under **GPL-3.0-or-later** to stay
  compatible with the reference project, and credit the reference in `README.md` and source headers.
* If any reference file (schematic fragment, footprint, firmware function) is copied later, the original
  copyright notice must be kept, the modification marked with date, and the combined work distributed under
  GPL-3.0 with source (GPL-3.0 §4, §5).
* The reference repository content in this Git repository is left **unmodified**.
