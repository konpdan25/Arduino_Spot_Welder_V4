# 02 — Architecture Comparison and Selected Candidate

| Item | Value |
|---|---|
| Document | DIY_SPOT_WELDER_V1 / 02_ARCHITECTURE_COMPARISON — Rev A (2026-10-12) |
| Inputs | Doc 01 (reference analysis), doc 03 (calculations), `Calculations/Engineering_Models/weld_calc.py` |
| Status | **Recommendation only. No high-current build is authorised** until the open items in §7 are closed. |

Legend: **[CALC]** computed in doc 03 · **[DS]** datasheet · **[DS3]** third-party copy of a datasheet · **[ASM]** assumption · **[UNK]** unknown.

---

## 1. Requirements recap

* Resistance spot welding of **0.15 mm pure nickel** onto 18650 cells.
* Repeatable energy → pulse duration repeatable to ≪ 5 % and a current that does not collapse during the pulse.
* Safe failure: no sustained current after a fault, MCU not the only means of ending a pulse.
* Reuse inventory where it is technically sound.

## 2. Source feasibility (applies to every architecture)

The welding source decides the achievable current far more than the switch does.

| Source | R_source | Estimated I_peak (best / typ / worst) [CALC] | Terminal voltage during pulse | Weld-zone power (typ) |
|---|---|---|---|---|
| **Ritar RT1270 12 V 7 Ah** (stock) | 25 / 32 / 45 mΩ ([DS3] ≤ 32 mΩ AC) | **388 / 294 / 202 A** | ≈ 3.2–3.3 V | ≈ 130 W |
| Car battery 45–60 Ah, 400–600 A EN (reference design) | 4 / 6 / 9 mΩ [ASM] | 1633 / 1027 / 623 A | ≈ 6.4–6.8 V | ≈ 1580 W |

Findings:

1. The RT1270 datasheet copy gives **70 A maximum for 5 s** [DS3]. The estimated weld current is **≈ 4× that value**. Behaviour at 200–400 A for tens of milliseconds is **not specified by the manufacturer** → battery damage, terminal heating and venting cannot be excluded.
2. The RT1270 uses **FASTON tabs (F1 4.8 mm / F2 6.3 mm)**. A push-on connection is not suitable for 300 A pulses.
3. The battery terminal voltage collapses to ≈ 3 V during a weld. Any circuit powered directly from the battery (relay coil, gate driver, MCU) would brown out **in the middle of the pulse** → MOSFETs drift into linear mode, relays drop out under load. Hence the diode-isolated hold-up banks in our design.
4. The weld-zone power is ≈ 12× lower than with the reference's car battery. Delivering a comparable energy needs ≈ 12× longer pulses, which spreads the heat into the cell (cell damage risk) and exceeds the MOSFET thermal limit (doc 03 §4). **Our engineering estimate is that the RT1270 is not a suitable welding source for 0.15 mm nickel.** This is an estimate; it must be confirmed or refuted by a controlled measurement (RELEASE_CHECKLIST step M1) — not by welding cells.

**Recommendation:** keep the RT1270 for bench validation of the electronics only (with a current-limiting dummy load, ≤ 50 A), and plan for a source that is specified for high pulse currents (e.g. a 45–60 Ah automotive starter battery, or a purpose-built high-rate LiFePO₄ pack with a BMS rated for the pulse current). Changing the source to a car battery requires the **power-stage variant P2** (§5.3), because 6× IRLZ44N cannot carry 600–1600 A.

## 3. Architecture A — relay as the welding switch

The original idea: the 12 V "≈100 A" relay switches the welding pulse, an H-bridge drives the coil.

| Criterion | Assessment |
|---|---|
| Pulse timing | Typical power relays operate in 5–15 ms and release in 2–10 ms with contact bounce of 1–5 ms [ASM, typical relay datasheets]. Variation of operate/bounce of ±1–3 ms on a 10 ms pulse is ±10–30 % energy. **Not repeatable enough** for weld pulses of 5–50 ms, and the double pulse (1–5 ms pre-pulse) is impossible. |
| Making current | The contacts would make the full short-circuit-like current (200–400 A) on every weld, with bounce → arcing during every closure. |
| Breaking current | The contacts would break 200–400 A DC on every weld. DC arcs do not self-extinguish at a zero crossing. A marking of "100 A" is usually an AC resistive or a 14 V automotive carrying rating [UNK for this part]. |
| Contact welding risk | **High.** A welded contact means an uncontrolled sustained current through the cell — the most dangerous failure mode in this application. |
| Coil drive / H-bridge | An H-bridge only helps if the relay is a **latching (bistable) type**. Relays from electricity-meter production are frequently 100 A *latching* meter-disconnect relays. **A latching relay keeps its state when power is removed → it is not fail-safe and must not be the safety isolation device.** For a monostable relay, a transistor with a fast-release clamp is simpler and equally good; the H-bridge adds no safety. |
| Fault behaviour | A stuck relay cannot be detected before it causes the hazard. |
| Verdict | **REJECTED as pulse switch.** |

## 4. Architecture B — MOSFET pulse switch only

| Criterion | Assessment |
|---|---|
| Timing | µs-resolution, edges ≈ 100 ns–1 µs, jitter < 10 µs with a timer ISR [CALC]. |
| Current | 6× IRLZ44N (stock): stage resistance ≈ 5.9 mΩ hot [CALC], IDM margin 2.0–2.7× at 294–388 A. |
| Thermal | At ≈ 300 A and T_case 50 °C, max ≈ 53 ms single pulse for T_j ≤ 150 °C; at 388 A ≈ 17 ms [CALC, assumed Zth(t)]. Firmware hard limit 50 ms + derating. |
| Failure | MOSFETs predominantly **fail short** (thermal or avalanche damage). With no series isolation, a short gives a sustained current limited only by the battery and the fuse. |
| Isolation | None → requires an independent disconnect. |
| Verdict | Good switching, insufficient fault isolation on its own. |

## 5. Architecture C — MOSFET pulse switch + carry-only isolation relay + fuse + manual disconnect (**SELECTED CANDIDATE**)

```
BT1(+) ─ F101 ANL ─ S101 disconnect ─ P_BUS ─ K101 (closed before, opened after) ─ E+ ~ workpiece ~ E− ─ DRAIN_BUS
                                      │                                                                │
                                      ├─ D101 STPS3045CP free-wheel (cathode) ◄──────── anodes ────────┤
                                      ├─ C101 1000 µF + D102 SMBJ24CA                        6× IRLZ44N (10 Ω / 10 k per gate)
BT1(−) ═════════════════════ SOURCE bar = GND star point ◄──── control board GND ────────────── sources
```

### 5.1 Why C

* MOSFETs do all switching (timing, double pulse).
* The relay **never makes or breaks the welding current by design**: it closes during ARMING (after the MOSFET self-test, gates off) and opens on DISARM/fault. It provides an independent series break against a shorted MOSFET (firmware detects the battery sag and opens it within ≈ 5–15 ms) and gives reverse-polarity protection of the power path (relay stays open if the control board is not powered).
* F101 + S101 are the hardware backstop when everything else fails (welded relay + shorted MOSFET).
* The two-pole E-STOP/ARM chain removes the relay coil supply **and** the gate-driver supply in hardware.

### 5.2 Limitations (stated, not hidden)

* K101 ratings are **unknown**. If it is a latching relay → replace (not fail-safe). Opening it under 300 A in a fault will arc and may weld the contacts; the fuse remains the final protection.
* Fuse coordination is poor with a weak source: weld current ≈ fault current (doc 03 §10). F101 cannot discriminate a long fault from a weld quickly; it protects the cable and battery against a sustained short (seconds), not against a cell being overheated.
* No current shunt in V1; current is an **estimate** from V_DS (± 30 %).

### 5.3 Power-stage variants

| Variant | Source | Switch | Status |
|---|---|---|---|
| **P1** | RT1270 (bench only) | 6× IRLZ44N (stock) on copper busbars | Designed, provisional |
| P2 | 45–60 Ah car battery (≤ 1.2 kA est.) | ≥ 8× 40 V MOSFETs with RDS(on) ≤ 1.5 mΩ (e.g. IRFB7430/IRFS7430 class, as reference V3/V4) | Not designed (purchase; same control board) |

The control board (gate driver TC4422 9 A, interlocks, firmware) is common to both variants.

## 6. Control solution comparison

| Option | Timing | Fault handling | Complexity | Cost | Verdict |
|---|---|---|---|---|---|
| **Arduino Nano (ATmega328P)** | Timer1 ISR, 4 µs ticks, jitter ≈ 2–5 µs | WDT, deterministic pins hi-Z in reset, 5 V logic matches TC4422/74HCT14/LM393 | Low | ≈ €5–22 (purchase) | **SELECTED** |
| DFRobot **DFR0868** (stock) | **Not a timer module**: it is the *Beetle ESP32-C3* development board. Hardware timers/RMT give µs timing. | 3.3 V I/O, boot-strapping pins (GPIO2/8/9), USB/JTAG pins glitch at reset; Wi-Fi/BLE stack adds complexity | Medium | €0 (stock) | Alternative only; pinout not verified here; would need level adaptation and a full glitch analysis of the weld pin |
| Hardware timer only (e.g. 555 monostable) | ms resolution, tolerance of RC (±10–20 %) | No supervision, no interlocks except hardware | Low | Low | Rejected (no measurement, no fault latching) |
| Hybrid MCU + independent hardware limits | — | MCU for control; **RC limiter + UVLO + E-STOP/ARM independent** | Medium | — | **Implemented** (Nano + LM393 limiter/UVLO) |

## 7. Decision record

| # | Decision | Status |
|---|---|---|
| D-1 | Architecture C (MOSFET pulse + carry-only isolation relay + fuse + disconnect) | Selected candidate |
| D-2 | Relay as pulse switch | Rejected |
| D-3 | H-bridge (DRV887x) for the relay coil | Rejected (no benefit for a monostable relay; latching relay unsuitable) |
| D-4 | 6× IRLZ44N in parallel, 10 Ω + 10 k per gate, TC4422 | Provisional (P1 only) |
| D-5 | IXFH20N50P3, STP6NK60 | Rejected (RDS(on) 0.3 Ω / ≈1 Ω) |
| D-6 | TC4421 (inverting) | Rejected for weld gate (default-on with pull-down) |
| D-7 | Arduino Nano + hardware limiter/UVLO | Selected |
| D-8 | RT1270 as welding source | **User decision 2026-10-12: proceed with RT1270 (variant P1).** Engineering estimate unchanged: outside datasheet ratings, weak weld power. Conditions: M1 measurement, bolted tab adapters, staged tests per RELEASE_CHECKLIST |
| D-9 | Control PCB without any welding-current conductors; welding current on copper busbars and 16 mm² cable | Selected |

**Blocking open items before any battery-connected high-current test:** K101 identification (type, DC rating, latching or not, drop-out voltage), source decision (RT1270 measurement or replacement), F101 selection with real I²t data, IRLZ44N authenticity check, busbar/heatsink mechanical design review. See `OPEN_ISSUES.md`.
