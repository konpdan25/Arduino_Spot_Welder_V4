# 04 — Safety Risk Register and Failure-Mode Analysis

| Item | Value |
|---|---|
| Document | DIY_SPOT_WELDER_V1 / 04_SAFETY_RISK_REGISTER — Rev A (2026-10-12) |
| Scope | Control PCB, power assembly (P1: RT1270 + 6× IRLZ44N), firmware 0.1.0-prelim, operation on 18650 cells |
| Method | Hazard identification + simplified FMEA. Severity S1 (minor) … S4 (fire, serious burn, explosion). Likelihood L1 (remote) … L4 (likely), **before** and **after** controls. |
| Status | Analysis only. **No control listed here has been verified on hardware.** Residual ratings are targets that the RELEASE_CHECKLIST must confirm. |

This design cannot be called "safe" on the basis of this document. It describes the intended protection layers and their known gaps.

---

## 1. Protection layers (defence in depth)

| Layer | Implementation | Independent of MCU? | Verified? |
|---|---|---|---|
| L0 | Main fuse F101 (ANL, provisional 150 A) near battery + | yes | no |
| L1 | Manual disconnect S101 | yes | no |
| L2 | E-STOP S102 (2 NC): pole A removes relay coil supply, pole B removes gate-driver supply | yes | no |
| L3 | ARM switch S103 (2 NO), same two poles | yes | no |
| L4 | R45 pull-down on GIN; non-inverting TC4422; 10 k G-S per MOSFET; R4 gate bus pull-down | yes | no |
| L5 | U3A RC pulse-length limiter (63–96 ms per ON interval) | yes | SPICE only |
| L6 | U3B gate-drive UVLO (8.0 V) | yes | SPICE only |
| L7 | K101 normally-open isolation relay, carry-only, opened by firmware on faults and by L2/L3 in hardware | partly | no |
| L8 | Firmware: hard pulse limits, latched faults, arming self-tests (UVLO, limiter, relay), stuck-current detection, thermal derating, watchdog | no | host simulation only |
| L9 | D101 free-wheel diode + C101/D102 bus clamp (prevents repetitive avalanche) | yes | SPICE only |
| L10 | Operator PPE and procedure (eye protection, no rings/watches, fire-safe surface, cell fixture) | — | — |

## 2. Hazard register

| ID | Hazard | Cause | Consequence | S | L before | Controls | L after | Residual / verification |
|---|---|---|---|---|---|---|---|---|
| H-01 | Sustained welding current into a cell | MOSFET fails short (thermal, avalanche, ESD, counterfeit) | Cell overheating → venting / thermal runaway, burns | 4 | 3 | L9 reduces avalanche stress; thermal limits (doc 03 §4); firmware STUCK_CURRENT → K101 opens (≈ 5–15 ms) ; F101; S101; E-STOP removes relay coil supply | 2 | **Relay must open under ≈ 300 A once** – may arc/weld (K101 unrated). Verify: RELEASE_CHECKLIST H5, H8 with dummy load. |
| H-02 | Sustained current | K101 contacts welded **and** MOSFET short | as H-01 | 4 | 1 | Boot/arming check RELAY_WELDED (non-clearable); F101; S101 | 1 | Depends on fuse clearing time (seconds) – a cell can be damaged before the fuse opens. Operator must keep S101 within reach. |
| H-03 | Pulse much longer than set | Firmware hang with gate high | Overheated weld, cell damage, MOSFET overheating | 4 | 2 | Timer1 ISR ends pulses independently of the main loop; watchdog (250 ms); **U3A cuts after 63–96 ms**; firmware verifies U3A at every ARM | 1 | HW limit 96 ms > FW 50 ms: a 96 ms pulse at 300 A is above the MOSFET thermal estimate (worst case) – acceptable as fault-only event; verify H3. |
| H-04 | Unintended weld | Noise / glitch on foot switch line | Weld on wrong position, burns | 3 | 3 | Pull-up + RC + Schmitt (74HCT14) + 30 ms debounce + continuous confirmation for 150–2000 ms (reference bug fixed); ARM switch | 1 | Tested in host simulation; verify on hardware with burst/ESD injection (H6). |
| H-05 | Unintended weld at power-up / reset | MCU pins floating, bootloader activity | as H-04 | 3 | 2 | Pins hi-Z → R45 keeps GIN low; gate pin forced low in `.init3`; ARM-at-boot and foot-at-boot faults; relay open until arming completes | 1 | Verify with scope during power cycling and USB programming (H1). |
| H-06 | MOSFETs in linear mode | Gate supply sags (weak battery) | MOSFET destruction → H-01 | 4 | 3 | Diode-isolated hold-up banks; UVLO 8 V (HW) + 9 V (FW) | 1 | Verify droop with dummy load (E4). |
| H-07 | Repetitive avalanche / overvoltage at turn-off | Cable inductance (≈ 65–113 mJ) | MOSFET degradation → H-01 | 3 | 3 | D101 free-wheel; C101 + D102; V_DS peak 16 V in SPICE | 1 | Verify with scope at the drain (H4). |
| H-08 | Battery damage, venting, hydrogen | 200–400 A pulses from a 7 Ah VRLA (≈ 4× datasheet max) | Case swelling, acid/electrolyte, explosion risk if ignited | 4 | 3 | **RT1270 NOT APPROVED as welding source**; bench tests ≤ 50 A dummy load only; ventilated area | 2 | Decision pending (OPEN_ISSUES OI-01). |
| H-09 | Terminal overheating / arcing | FASTON tabs carrying 300 A | Burn, fire, battery damage | 3 | 4 | Not permitted; if the RT1270 is ever used: bolted/soldered tab adapters, measured temperature rise | 2 | OI-01 |
| H-10 | Short circuit of battery during assembly | Tool / busbar contact | Arc flash, burns, fire | 4 | 2 | F101 within 150 mm of battery +; S101 open during work; insulated busbars; procedure | 1 | Procedure in doc 05 |
| H-11 | Reverse battery connection | Assembly error | Body diodes conduct → uncontrolled current through workpiece | 4 | 2 | K101 normally open and only closed after VBAT ≥ 11.5 V is measured (reverse → reads 0 V → cannot arm; control board unpowered via D1/D2 → relay cannot close); D3 + fuses clear a reversed tap | 1 | Verify with a current-limited reversed supply (E6). |
| H-12 | Burns from electrodes / nickel | Hot tips after repeated welds | Skin burns | 2 | 3 | Duty limit 5 %; insulated electrode holders; procedure | 2 | — |
| H-13 | Eye injury | Weld spatter/sparks | Eye damage | 3 | 2 | Safety glasses mandatory (doc 05) | 1 | — |
| H-14 | Overheating of power assembly | High duty cycle | Insulation damage, fire | 3 | 2 | NTC on drain bar → derating 40–60 °C, lock-out 60 °C; NTC open/short detection | 1 | NTC B value unknown → calibrate (E7). Firmware-only protection (not independent). |
| H-15 | Electric shock | none (≤ 15 V system) | — | 1 | 1 | SELV voltage levels | 1 | Charger must not be connected while welding (OV fault at 14.8 V). |
| H-16 | Drain bar / heatsink at electrode potential touches enclosure | Mechanical | Unintended current path / short | 3 | 2 | Insulate bar from enclosure, non-conductive enclosure, ≥ 1.5 kV insulating pads where needed | 1 | Mechanical review (doc 05). |
| H-17 | Wrong firmware settings | User error | Weak or over-heated welds | 2 | 3 | Compile-time hard limits; menu only in DISARMED/READY | 2 | — |
| H-18 | Relay drops out under load | Coil hold-up insufficient | Arc, contact welding → H-02 | 3 | 2 | Separate relay hold-up bank (14.7 mF); FW limit keeps VHOLD_RELAY > 9.4 V (calc) | 2 | Drop-out voltage unknown → measure (M4). |
| H-19 | Ground loop through control wiring | Control GND tied to battery − and source bar separately | Weld current in thin wires → burnt wires, false readings | 3 | 2 | Single star point at the source bar for J1.2 and J3.2/J3.6 | 1 | Wiring inspection |
| H-20 | Latching (bistable) relay used as K101 | Inventory relay from meter production may be latching | No fail-safe opening on E-STOP / power loss | 4 | 2 | Identify relay; reject if latching | 1 | OI-02 |

## 3. FMEA — key components (single faults)

| Item | Failure mode | Effect | Detection | Mitigation |
|---|---|---|---|---|
| Q101–Q106 | short D-S | H-01 | STUCK_CURRENT (battery sag), relay open | fuse, disconnect |
| Q101–Q106 | open / gate open | less current, other devices overloaded | weaker weld, V_DS higher | per-gate pull-down keeps it off; inspect |
| TC4422 | output stuck high | sustained gate | GATE_FB low (stuck) not detectable: FB is upstream of the driver → **not detected by firmware**; STUCK_CURRENT detects the effect | E-STOP pole B removes VDD |
| TC4422 | output stuck low | no weld | missing V_DS drop / no current | — |
| U3 (LM393) | output stuck low | no welding | ARM limiter test: FB never rises → fault | — |
| U3 | output open (no limit) | loss of L5/L6 | ARM limiter test (FB does not fall) → non-clearable fault | — |
| R45 open | GIN floats when MCU in reset | possible spurious gate | not detected | TC4422 input + R44 path; ARM switch must be off when programming (procedure) |
| C29 (timing) | value drift | limiter window shifts | ARM test window 50–120 ms | film capacitor |
| K101 | contacts welded | no isolation | RELAY_WELDED at boot / arming | fuse, disconnect |
| K101 | does not close | no weld | RELAY_NO_CLOSE | — |
| D101 | open | avalanche at every pulse | not detected | inspection; V_DS check during commissioning |
| D101 | short | DRAIN_BUS tied to P_BUS: welding cables bypassed; every pulse shorts the battery through the MOSFETs (no weld, very high MOSFET stress) | no weld + very low VBAT during pulse; fuse | diode test of D101 before first power-up |
| NTC | open/short | no thermal protection | NTC_INVALID fault | — |
| Hold-up caps | dry-out | rails droop | VHOLD/VDRV checks, UVLO | — |
| Nano | crash | — | watchdog reset → WDT_RESET fault latched | HW limiter |

## 4. Limitations that remain (must be communicated)

1. **MOSFET short failure is the dominant hazard.** The only actions after it are: firmware opening an unrated relay, the fuse (seconds), and the operator. A cell under the electrodes can be damaged before the fuse acts.
2. The TC4422 output is not monitored (GATE_FB is upstream). An optional future improvement: read back the gate bus (GATE_OUT) through a divider.
3. Temperature protection is firmware-only.
4. No measured data supports any rating in this project.
5. ERC/DRC/simulation results are consistency checks, not safety approval.

## 5. Mandatory operating rules (until validation is complete)

* No battery-connected high-current test, no cell welding, no manufacturing release on the basis of analysis, ERC, DRC or simulation.
* Bench validation of the control board with a **current-limited lab supply** and a **dummy load** only (RELEASE_CHECKLIST stages E and H).
* Eye protection, fire-safe workplace, Class D/ABC extinguisher, cells in a fixture, S101 within reach.
