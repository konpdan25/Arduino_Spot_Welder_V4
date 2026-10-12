# 05 — Manufacturing, Assembly and DFM Requirements

| Item | Value |
|---|---|
| Document | DIY_SPOT_WELDER_V1 / 05_MANUFACTURING_AND_ASSEMBLY — Rev A (2026-10-12) |
| Release state | **PRELIMINARY — NO MANUFACTURING RELEASE.** No Gerber/drill/pick-and-place files are generated on purpose. The power stage is unresolved (doc 02 §7). |

---

## 1. Control PCB (KiCad: `KiCad/DIY_SPOT_WELDER_V1.kicad_pcb`)

| Parameter | Value |
|---|---|
| Size | 190 × 140 mm, 4× M3 isolated mounting holes |
| Stack-up | 2 layers, FR-4, 1.6 mm, 35 µm (1 oz) — **no welding current on this board** |
| Technology | Through-hole except D3 (SMB) and U7 (MSOP-8) |
| Net classes | Default 0.25 mm / 0.2 mm; Power 0.8 mm / 0.2 mm; Gate 0.6 mm / 0.25 mm; Sense 0.3 mm / 0.25 mm |
| Copper pours | GND on both layers (thermal reliefs) |
| Routing | Freerouting 1.9.0 autorouter → **preliminary**; one connection (ENC_SW_RAW) is left unrouted and must be finished by hand; GND pour connectivity and return paths need a manual review |
| DRC (KiCad 7.0.11) | 0 clearance / short violations; 1 unconnected item; thermal-relief and silkscreen warnings (see `Reports/DRC/DRC_REPORT_KiCad7.txt`) |

### 1.1 Layout requirements to be checked/improved manually in KiCad 10

1. Keep TC4422 (U4), C13, C14 and J3 close together; route GATE_OUT and the GND return of J3 pin 2 as a pair.
2. Hold-up capacitors C1/C2/C4/C5: verify the real diameters and lead pitch of the stock capacitors and adapt the footprints (provisional: 18/16/22/16 mm).
3. Analog inputs (ADC_*) away from GATE_DRV/GATE_OUT and RELAY_COIL_N.
4. Add a clear silkscreen warning near J3/J4/J1 (pinout + "NO WELDING CURRENT").
5. Replace autorouted power traces (VHOLD_*, VDRV) by short, direct traces; make sure the GND pours are not fragmented under U3/U4.
6. Re-run DRC with schematic parity in KiCad 10 (README §Validation).

### 1.2 Assembly order (control PCB)

1. Low-profile parts: resistors, diodes (check polarity: band = cathode = pad 1), ceramic capacitors, D3 (SMB) and U7 (MSOP, use flux and a fine tip).
2. IC sockets (DIP-8 ×2, DIP-14), TO-92 parts (BC337, BC547, MCP1700), LEDs, button, buzzer.
3. Connectors (J1–J7), fuse holder F1, R1 (mount 2 mm above the board), U2 7805.
4. Large electrolytic capacitors last (check polarity).
5. **Before inserting ICs:** power J1 from a current-limited lab supply (12 V, 200 mA) → check VHOLD_LOGIC, VHOLD_RELAY, +5V_AUX, +3V3 at the test points.
6. Insert U3/U4/U5, the Nano and the OLED; follow `RELEASE_CHECKLIST.md` stage E.

## 2. Power assembly (provisional mechanical design — not released)

```
                 drain copper bar 200x25x5 (heatsink + DRAIN_BUS + electrode− lug)
   ┌────────────────────────────────────────────────────────────────────┐
   │ [Q101] [Q102] [Q103] [Q104] [Q105] [Q106]   tabs bolted M3 + thermal compound (tab = drain)
   └──────┬───────┬───────┬───────┬───────┬───────┬─────────────────────┘
          │ G D S │ (TO-220 legs bent, S legs soldered to source bar, G to gate strip)
   ═══════╧═══════╧═══════╧═══════╧═══════╧═══════╧══ source copper bar 200x15x3 = GND star point
      gate strip: 10 R + 10 k per MOSFET (point-to-point or a small strip board), twisted pair to J3
   D101 STPS3045CP: anodes → drain bar, tab (cathode) → P_BUS bar (insulated from drain bar!)
   C101 1000 µF + D102 SMBJ24CA directly between P_BUS bar and source bar
```

Requirements:

* Equal-length, symmetric source connections for the six MOSFETs (current sharing). Solder source legs over their full length to the bar or use M3 lugs; avoid thin PCB tracks in the current path.
* Drain bar is at electrode potential: insulate it from the enclosure (≥ 1.5 kV insulating pads / stand-offs) or use a non-conductive enclosure.
* NTC TH101 glued to the drain bar with Kapton + thermal epoxy (electrically insulated).
* Cable lugs: copper tube lugs crimped with a hexagonal crimp tool for 16 mm² (no solder-only joints in the high-current path), heat-shrink.
* Tighten M6 lugs with a defined torque (per lug manufacturer), use spring washers; re-check after the first thermal cycles.
* Keep both welding cables together (twisted or taped) → loop inductance lower.
* F101 within 150 mm of the battery positive terminal; S101 accessible from the operator position.
* Single-point ground: J1.2 and J3.2/J3.6 to the same screw on the source bar; battery − cable to the same bar.

## 3. Wiring list

| From | To | Wire |
|---|---|---|
| BT1 + | F101 | 16 mm², ≤ 150 mm |
| F101 | S101 | 16 mm² |
| S101 | P_BUS bar (K101 contact 13, D101 cathode, C101+, D102, F102) | 16 mm² |
| K101 contact 14 | Electrode + | 16 mm² silicone, 0.5 m |
| Drain bar | Electrode − | 16 mm² silicone, 0.5 m |
| BT1 − | Source bar | 16 mm² |
| P_BUS bar via F102 3 A | J1.1 | 0.5 mm² |
| Source bar | J1.2 | 0.5 mm² |
| Gate strip / source bar | J3.1 / J3.2 | twisted pair AWG24, ≤ 150 mm |
| Drain bar / source bar | J3.3 / J3.6 | twisted pair AWG24 |
| K101 contact 14 | J3.4 | AWG24 |
| TH101 | J3.5 / J3.6 | twisted pair AWG24 |
| K101 coil A1/A2 | J4.1 / J4.2 | 0.5 mm² |
| S102/S103 two-pole chain | J2.1–J2.4 | 0.5 mm² |

## 4. DFM review notes

| Topic | Note |
|---|---|
| Part availability | STPS3045CP is listed as obsolete by some distributors → stock part only; replacement e.g. any 45 V ≥ 2×15 A common-cathode Schottky in TO-247/TO-220. |
| Hand assembly | All parts hand-solderable; U7 MSOP-8 is the hardest. |
| Sockets | DIP sockets for U3/U4/U5 and headers for the Nano/OLED → serviceable, but socket contact reliability must be checked (the reference V3 had socket problems with the gate driver). Consider soldering U4 directly after validation. |
| Test access | 17 test points (TP1–TP17) for all rails and the interlock nodes. |
| Labelling | Connector pin functions on silkscreen; ARMED LED (hardware) visible from the operator position. |
| Conformal coating | Not required for a dry indoor environment. |

## 5. Outputs intentionally NOT generated

Gerber, drill, pick-and-place, assembly drawings: withheld until the release criteria in `RELEASE_CHECKLIST.md` are met (engineering rule: no manufacturing-ready outputs for an unresolved high-current power stage).
