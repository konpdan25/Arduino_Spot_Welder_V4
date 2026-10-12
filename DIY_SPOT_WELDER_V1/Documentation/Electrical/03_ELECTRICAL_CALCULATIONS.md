# 03 — Electrical Design Calculations and Limitations

| Item | Value |
|---|---|
| Document | DIY_SPOT_WELDER_V1 / 03_ELECTRICAL_CALCULATIONS — Rev A (2026-10-12) |
| Model | `Calculations/Engineering_Models/weld_calc.py` → full output in `Reports/Validation/CALCULATION_RESULTS.md` |
| SPICE | `Calculations/SPICE/*.cir` (ngspice 42, behavioural models) → `Reports/Validation/SPICE_RAW_OUTPUT.txt` |
| Nature of results | **All values are estimates.** Nothing in this document is a measurement. Parameter origins are tagged in the model (DS / DS3 / ASM). |

---

## 1. Assumptions that dominate the results

| Parameter | Range used | Origin | How to replace by a measurement |
|---|---|---|---|
| RT1270 internal resistance | 25 / 32 / 45 mΩ | DS3 (≤ 32 mΩ, AC, full charge) + DC-pulse margin | 4-wire pulse test: ΔV/ΔI with a 20–50 A load step (M1) |
| Weld-zone resistance | 0.5 / 1.5 / 3.0 mΩ | ASM | V-I measurement across electrodes on nickel during a pulse |
| Relay contact resistance | 0.2 / 0.6 / 1.5 mΩ | ASM (unknown part) | 4-wire at 10 A DC (M3) |
| Joints (6–10) | 0.05–0.2 mΩ each | ASM | mV drop at 10–50 A |
| IRLZ44N RDS(on) | 22 mΩ max (10 V, 25 °C) × 1.45–1.75 (hot) | DS / curve | — |
| Current sharing worst device | 1.10–1.30 × average | ASM | measure V_DS of each device not possible; use matched batch + symmetric layout |
| Zth(t) | RthJC·√(t/τ), τ = 0.2–0.4 s | ASM fit | replace with the datasheet Zth curve |

## 2. Loop resistance budget [CALC]

| Element | best | typ | worst (mΩ) |
|---|---|---|---|
| Battery leads 2× 16 mm² (0.5–0.8 m total) | 0.54 | 0.64 | 0.86 |
| Welding cables 2× 16 mm² (0.8–1.2 m total) | 0.86 | 1.07 | 1.29 |
| Electrode tips | 0.10 | 0.15 | 0.25 |
| Joints | 0.30 | 0.80 | 2.00 |
| Fuse ANL/MIDI | 0.30 | 0.45 | 0.70 |
| Relay contacts | 0.20 | 0.60 | 1.50 |
| Disconnect | 0.10 | 0.15 | 0.30 |
| 6× IRLZ44N (hot) | 5.33 | 5.88 | 6.44 |
| Weld zone | 0.50 | 1.50 | 3.00 |
| **R_ext total** | **8.22** | **11.25** | **16.34** |

Cable: R = ρ·L/A, ρ_Cu = 1.72·10⁻⁸ Ω·m.

## 3. Current envelope and source behaviour [CALC]

I = V_OC / (R_source + R_ext);  V_term = V_OC − I·R_source;  P_weld = I²·R_weld

| Source | Case | I_peak | V_term during pulse | P_weld-zone |
|---|---|---|---|---|
| RT1270 | best | 388 A | 3.19 V | 75 W |
| RT1270 | typ | 294 A | 3.30 V | 129 W |
| RT1270 | worst | 202 A | 3.30 V | 123 W |
| Car battery (ref., 1 mΩ switch) | typ | 1027 A | 6.54 V | 1581 W |

* RT1270 typical current = **4.2 × the 70 A (5 s) datasheet maximum** [DS3].
* Weld-zone power is **≈ 12× lower** than with a car battery.
* The battery terminal collapses to ≈ 3.3 V → everything supplied directly from it browns out (basis for §7).

## 4. MOSFET stress (6× IRLZ44N, worst-shared device) [CALC]

Iterated: P = I_dev²·RDS(T_j), T_j = T_case + P·Zth(t).

| I_total | Case | I/device | Max single pulse for T_j ≤ 150 °C |
|---|---|---|---|
| 200 A | typ (T_case 50 °C) | 40 A | 244 ms |
| 294 A | typ | 59 A | **53 ms** |
| 294 A | worst (T_case 65 °C, share 1.3) | 64 A | 15 ms |
| 388 A | typ | 78 A | 17 ms |
| 450 A | typ | 90 A | 10 ms |

Consequences implemented: firmware hard limit **50 ms main / 65 ms total ON**; derating from 40 °C (50 ms) to 60 °C (20 ms), lock-out at 60 °C; duty limit (interval ≥ 20 × ON time). IDM margin is 2.0–2.7× at 294–388 A.

Average dissipation at 1 weld / 2 s (65 ms ON, typ): ≈ 4.3 W/device, 26 W into the drain bar → heatsink Rth ≤ 1.5 K/W for ≈ 40 K rise [CALC].

**Limitation:** current sharing between six TO-220 devices on a busbar is not guaranteed; the worst-case column must be treated as the design point until measured temperatures confirm otherwise.

## 5. Gate drive

* TC4422 VDD = VDRV ≈ VHOLD_LOGIC − 0 V (via ARM chain) ≈ 10–11.4 V; VGS(max) IRLZ44N ±16 V [DS] → D4 BZY97C15 clamp + R3 2.2 Ω.
* Gate charge (estimate) ≈ 50–80 nC per device at 10 V → ≈ 0.5 µC total; C14 47 µF droop ≈ 10 mV per edge.
* Per-device path: 2.2 Ω (common) + 10 Ω + TC4422 R_out ≈ 1.5 Ω → ≈ 0.8 A per gate peak, edges of a few hundred ns. Slower than the minimum possible on purpose (lower di/dt, less ringing in a busbar layout).
* **UVLO (U3B):** trips when VDRV < 2.5 V × (22k+10k)/10k = **8.0 V** (hardware); firmware requires ≥ 9.0 V. IRLZ44N is specified at 4–10 V V_GS; 8 V keeps it well enhanced.
* **Default off:** R45 22 kΩ on GIN; TC4422 input leakage ≤ 10 µA → ≤ 0.22 V ≪ V_IL 0.8 V. MCU high level on GIN: 4.9 V × 22k/(2.2k+22k) = 4.45 V ≫ V_IH 2.4 V. LM393 sink ≈ 2.2 mA at V_OL ≈ 0.25 V.

## 6. Hardware pulse-length limiter (U3A) [CALC + SPICE]

V_CT(t) = V_OH·(1 − e^(−t/RC)), trip when V_CT = V_TH = V_CC·22k/32k.

Monte-Carlo (20 000 samples; R 68k ±1 %, C 1 µF −20/+10 %, V_CC 4.8–5.2 V, V_OH V_CC−0…0.2 V, V_os ±5 mV):

| min | median | max |
|---|---|---|
| **63 ms** | 78 ms | **96 ms** |

* Firmware limit per ON interval 50 ms → 13 ms margin to the hardware minimum.
* SPICE (`pulse_limiter.cir`, behavioural comparator): simulated firmware lock-up with GATE_CMD stuck high → GIN cut **73 ms** later; GIN stays low afterwards (0.13 V). A normal 40 ms pulse passes unaffected (GIN 4.45 V).
* The firmware verifies the limiter at every ARM (relay open): GATE_FB must fall between 50 and 120 ms.
* Reset: D8 + R48 discharge (τ = 4.7 ms) when GATE_CMD is low. A 2 ms minimum gap is enforced between pre- and main pulse.

## 7. Control rails and hold-up [CALC]

Pre-pulse bank voltage (worst): V_OC,min − V_F,max − I·R1 = 12.4 − 0.55 − 0.44 × 1.5 = **11.19 V**.

| Rail | C (min, −20 %) | Load | ON time | Droop | End voltage | Limit |
|---|---|---|---|---|---|---|
| VHOLD_LOGIC (C1 6800 + C2 2200 µF) | 7.2 mF | 0.11 A | 65 ms | 0.99 V | 10.2 V | UVLO 8.2 V max, 7805 ≥ 7 V |
| VHOLD_RELAY (C4 10000 + C5 4700 µF) | 11.8 mF | 0.33 A | 65 ms | 1.82 V | 9.4 V | relay drop-out **UNKNOWN** |
| VHOLD_LOGIC | 7.2 mF | 0.11 A | 96 ms (HW max) | 1.47 V | 9.7 V | |
| VHOLD_RELAY | 11.8 mF | 0.33 A | 96 ms | 2.69 V | 8.5 V | |

Inrush at connection: 8.6 A peak through R1 1.5 Ω, 2.4 J, I²t ≈ 1.6 A²s → F1 T3.15A (5×20) and a 5 W wire-wound R1.

## 8. Inductive energy, free-wheel and clamps [CALC + SPICE]

| Quantity | 294 A | 388 A |
|---|---|---|
| Welding-cable energy ½·L·I² (L = 1.5 µH worst) | 65 mJ | 113 mJ |
| Battery-lead energy (L = 0.4 µH worst) | 17 mJ | 30 mJ |

SPICE `weld_loop_turnoff.cir` (typical loop, 20 ms pulse, switch model without avalanche):

| Case | I_peak | V_DS on | Bus during pulse | V_DS peak at turn-off | Bus peak | I free-wheel peak |
|---|---|---|---|---|---|---|
| With D101 STPS3045CP | 297 A | 1.75 V | 3.03 V | **16.1 V** | 14.9 V | 297 A |
| Without free-wheel diode | 297 A | 1.75 V | 3.03 V | 7.4 kV (model; reality: MOSFET avalanche at ≈ 60 V on every pulse) | 26.4 V | 0 |

* Free-wheel time constant ≈ 0.4 ms; I²t per die ≈ 7.6 A²s vs. 242 A²s (220 A, 10 ms half-sine, DS3) → large margin.
* The 1000 µF bus capacitor absorbs the battery-lead energy; SMBJ24CA (V_BR ≥ 26.7 V) is a secondary clamp only.
* V_DS stays far below 55 V; no repetitive avalanche is expected with D101 in place.

## 9. Sensing and ADC

* All dividers 33k/10k → k = 4.30; full scale 21.5 V at AVCC = 5 V, **21 mV/LSB**; source impedance 7.7 kΩ (< 10 kΩ recommended for the ATmega ADC); 100 nF → τ = 0.77 ms.
* V_DS during a typical pulse ≈ 1.7 V → ≈ 80 LSB. Current estimate I = V_DS / R_stage with R_stage = 5.9 mΩ → **± 30 %** (RDS(T) spread, sharing). Displayed as "EST.".
* Battery minimum during the pulse is recorded; with the RT1270 it is ≈ 3.3 V (estimate).
* ARM_A sense: 10k/4.7k → 14.7 V → 4.7 V (HCT input max V_CC + 0.5 V).
* NTC: 10 kΩ pull-up to AVCC, 1 kΩ series; B value of the stock NTC **unknown** (3950 assumed).

## 10. Protection devices

| Item | Calculation | Result |
|---|---|---|
| Main fuse F101 | weld-pulse I²t (388 A, 65 ms) = **9.8 kA²s** per weld; fault: 300–390 A continuous | Choose pre-arc I²t ≥ 5 × pulse I²t (≥ 50 kA²s) **and** clearing time at 300–400 A short enough for the 16 mm² cable (adiabatic 3.4 MA²s → ≥ 22 s at 388 A). Candidate ANL 150 A — **PROVISIONAL**, needs the fuse datasheet. |
| Cable 16 mm² | k = 115 (PVC, conservative; silicone ≈ 141): I²t = (k·S)² | 22 s at 388 A |
| Relay coil clamp | V_CE,max = V_coil + V_F(1N4148) + V_Z(15 V) ≈ 12 + 0.7 + 15.6 | ≈ 28.3 V < 45 V (BC337) |
| BC337 base drive | (5 − 0.8 V) / 220 Ω | ≈ 19 mA → forced β ≈ 16 at 300 mA |
| SMBJ15A on VBAT_F | V_C 24.4 V @ 24.6 A [DS] | fuse F1 + R1 limit energy; caps behind diodes are 25 V |
| Gate clamp | BZY97C15 (13.8–15.6 V) + R3 2.2 Ω | VGS ≤ 16 V |

## 11. PCB conductor sizing (control board, ≤ 0.5 A per net)

* IPC-2221 external conductor, 35 µm, ΔT 10 K: 0.25 mm ≈ 0.8 A, 0.8 mm ≈ 2 A → Power class 0.8 mm (relay 0.3 A, hold-up recharge peaks ≈ 1–8 A for ms only), signals 0.25 mm.
* Clearance 0.2–0.25 mm at ≤ 15 V (IPC-2221 B2 requires 0.1 mm) — generous.
* **No welding current on the PCB.** Busbars: drain bar 25 × 5 mm Cu (125 mm², ≈ 0.14 mΩ per 100 mm), source bar 15 × 3 mm Cu (45 mm²) — provisional dimensions.

## 12. What is NOT known / not proven

* RT1270 pulse behaviour, K101 identity and ratings, actual weld-zone resistance, MOSFET current sharing, Zth curve, F101 I²t, stock capacitor dimensions/ESR, NTC B value, encoder module pinout.
* SPICE uses behavioural switches/comparators, not vendor models; no layout parasitics beyond the lumped L values.
* No thermal measurement of any kind has been made.
