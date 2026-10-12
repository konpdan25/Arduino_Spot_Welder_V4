#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""
DIY_SPOT_WELDER_V1 - engineering calculation model.

Every number produced here is an ESTIMATE built from the parameters below.
Parameters are tagged with their origin:
    DS   = manufacturer datasheet value (see Documentation/Datasheets/DATASHEET_INDEX.md)
    DS3  = value from a third-party copy / distributor listing of the datasheet (lower confidence)
    PHY  = physical constant / standard formula
    ASM  = engineering assumption (must be replaced by a measurement)
Nothing in this file is a measurement.

Usage:  python3 weld_calc.py  [--md OUTPUT.md]
"""
import argparse
import math
import random

RHO_CU = 1.72e-8          # PHY  ohm*m at 20 C (annealed copper)
ALPHA_CU = 0.00393        # PHY  1/K

# ----------------------------------------------------------------------------
# Parameter sets: (min, typ, max)
# ----------------------------------------------------------------------------
P = {
    # --- Ritar RT1270 -------------------------------------------------------
    "bat_ocv":        (12.4, 12.7, 12.9,  "V",   "ASM  open-circuit voltage 75 %..100 % SoC"),
    "bat_rint":       (0.025, 0.032, 0.045, "ohm", "DS3 <=32 mOhm (full charge, 25 C, AC method); DC pulse value assumed up to 45 mOhm"),
    "bat_imax_ds":    (70, 70, 70,       "A",   "DS3 max discharge current 70 A for 5 s"),
    # --- Car battery used by the reference (comparison only) -----------------
    "car_rint":       (0.004, 0.006, 0.009, "ohm", "ASM  45-60 Ah, 400-600 A EN starter battery"),
    # --- Conductors ---------------------------------------------------------
    "len_batlead_m":  (0.5, 0.6, 0.8,    "m",   "ASM  total length battery(+)->assembly + assembly->battery(-)"),
    "len_weld_m":     (0.8, 1.0, 1.2,    "m",   "ASM  total length of both welding cables"),
    "cs_cable_mm2":   (16, 16, 16,       "mm2", "ASM  16 mm2 fine-stranded silicone (as reference)"),
    "r_tips":         (0.10e-3, 0.15e-3, 0.25e-3, "ohm", "ASM  2 solid Cu electrodes ~40 mm, 10 mm2"),
    "n_joints":       (6, 8, 10,         "-",   "ASM  bolted/crimped joints in the loop"),
    "r_joint":        (0.05e-3, 0.10e-3, 0.20e-3, "ohm", "ASM  per clean crimp/bolt joint"),
    "r_fuse":         (0.30e-3, 0.45e-3, 0.70e-3, "ohm", "ASM  ANL/MIDI 100-150 A cold resistance (verify with fuse datasheet)"),
    "r_relay":        (0.20e-3, 0.60e-3, 1.50e-3, "ohm", "ASM  unknown used 100 A relay contacts (MUST be measured)"),
    "r_disconnect":   (0.10e-3, 0.15e-3, 0.30e-3, "ohm", "ASM  battery isolator switch"),
    "r_weld":         (0.5e-3, 1.5e-3, 3.0e-3,  "ohm", "ASM  electrode-Ni-cell contact + Ni path; falls during the weld"),
    # --- IRLZ44N power stage ------------------------------------------------
    "n_fet":          (6, 6, 6,          "-",   "STOCK at least 6 x IRLZ44N"),
    "rds_25":         (0.022, 0.022, 0.022, "ohm", "DS  RDS(on) max at VGS=10 V, ID=25 A, Tj=25 C"),
    "rds_tc":         (1.45, 1.6, 1.75,  "x",   "DS  normalised RDS(on) at Tj~125 C read from curve (approx.)"),
    "share":          (1.10, 1.20, 1.30, "x",   "ASM  worst-device current share factor for 6 parallel TO-220"),
    "r_fet_leads":    (0.05e-3, 0.08e-3, 0.12e-3, "ohm", "ASM  per device leads+solder to busbar"),
    "fet_idm":        (160, 160, 160,    "A",   "DS  pulsed drain current"),
    "fet_rthjc":      (1.8, 1.8, 1.8,    "K/W", "DS  RthJC TO-220 (IRLZ44N)"),
    "zth_tau":        (0.40, 0.30, 0.20, "s",   "ASM  Zth(t) ~ RthJC*sqrt(t/tau) (min=best); fit to typical TO-220 curves, verify on real datasheet"),
    "tj_limit":       (150, 150, 150,    "C",   "DESIGN derated junction limit for repetitive pulses"),
    "fet_tjmax":      (175, 175, 175,    "C",   "DS"),
    "t_case":         (35, 50, 65,       "C",   "ASM  drain busbar/heatsink temperature"),
    # --- Inductance ---------------------------------------------------------
    "l_weld":         (0.4e-6, 0.9e-6, 1.5e-6, "H", "ASM  welding cables (kept together vs. open loop)"),
    "l_bat":          (0.1e-6, 0.2e-6, 0.4e-6, "H", "ASM  battery leads, twisted, short"),
    # --- Control supply / hold-up -------------------------------------------
    "c_logic_uF":     (9000*0.8, 9000, 9000*1.2, "uF", "STOCK 6800 uF + 2200 uF / 25 V, +-20 %"),
    "c_relay_uF":     (14700*0.8, 14700, 14700*1.2, "uF", "STOCK 10000 uF + 4700 uF / 25 V, +-20 %"),
    "i_logic":        (0.060, 0.080, 0.110, "A", "ASM  Nano ~25 mA + OLED 20 mA + 7805/LDO Iq + LM393 + TC4422 Iq + LEDs"),
    "i_relay":        (0.27, 0.30, 0.33,   "A",   "USER ~300 mA relay coil at 12 V"),
    "r_tap":          (1.5, 1.5, 1.5,      "ohm", "DESIGN inrush/limit resistor in supply tap"),
    "vf_supply":      (0.35, 0.45, 0.55,   "V",   "DS  SB560/1N5822-class Schottky at ~0.4 A"),
    "uvlo_th":        (7.8, 8.0, 8.2,      "V",   "DESIGN gate-drive UVLO threshold"),
    "v_7805_min_in":  (7.0, 7.0, 7.0,      "V",   "DS  7805 min input at light load (Vout+2 V)"),
    # --- Pulse-length limiter (RC + LM393) -----------------------------------
    "pl_R":           (68e3*0.99, 68e3, 68e3*1.01, "ohm", "DESIGN 1 %"),
    "pl_C":           (1.0e-6*0.80, 1.0e-6, 1.0e-6*1.10, "F",  "DESIGN 1 uF X7R 50 V 1206, incl. DC-bias derating"),
    "pl_voh":         (4.6, 4.8, 5.0,      "V",   "DS  ATmega328P VOH at ~1 mA, VCC 4.8-5.2 V"),
    "fw_max_on_ms":   (50, 50, 50,      "ms",  "DESIGN firmware hard limit for one ON interval"),
}


def v(key, which=1):
    return P[key][which]


def cable_r(length_m, cs_mm2, temp_c=20.0):
    return RHO_CU * length_m / (cs_mm2 * 1e-6) * (1 + ALPHA_CU * (temp_c - 20))


def loop_resistances(case):
    """case: 0=min (best), 1=typ, 2=max (worst)"""
    i = case
    r = {}
    r["battery leads"] = cable_r(v("len_batlead_m", i), v("cs_cable_mm2", i))
    r["welding cables"] = cable_r(v("len_weld_m", i), v("cs_cable_mm2", i))
    r["electrode tips"] = v("r_tips", i)
    r["joints"] = v("n_joints", i) * v("r_joint", i)
    r["fuse"] = v("r_fuse", i)
    r["relay contacts"] = v("r_relay", i)
    r["disconnect"] = v("r_disconnect", i)
    rds_hot = v("rds_25") * v("rds_tc", i)
    r["MOSFETs (6x IRLZ44N, hot)"] = (rds_hot + v("r_fet_leads", i)) / v("n_fet")
    r["weld zone"] = v("r_weld", i)
    return r


def current_envelope(src_rint, ocv, rext):
    i = ocv / (src_rint + rext)
    vterm = ocv - i * src_rint
    return i, vterm


def holdup(c_uF, i_load, t_s):
    return i_load * t_s / (c_uF * 1e-6)


def pulse_limiter_window():
    # Vth set by divider from +5V (VCC): R1 = 10k (top), R2 = 22k (bottom) -> 0.6875
    # comparator compares RC voltage (charging from MCU VOH through R) against Vth
    out = []
    random.seed(1)
    res = []
    for _ in range(20000):
        vcc = random.uniform(4.8, 5.2)                    # 7805 +-4 %
        voh = vcc - random.uniform(0.0, 0.2)              # MCU output high at light load
        r1 = 10e3 * random.uniform(0.99, 1.01)
        r2 = 22e3 * random.uniform(0.99, 1.01)
        vth = vcc * r2 / (r1 + r2) + random.uniform(-0.005, 0.005)  # LM393 offset 5 mV max
        R = 68e3 * random.uniform(0.99, 1.01)
        C = 1.0e-6 * random.uniform(0.80, 1.10)
        if vth >= voh:
            continue
        t = -R * C * math.log(1 - vth / voh)
        res.append(t * 1e3)
    res.sort()
    return res[0], res[len(res) // 2], res[-1]


def zth(t, case):
    return min(v("fet_rthjc"), v("fet_rthjc") * math.sqrt(t / v("zth_tau", case)))


def fet_tj(i_total, t, case):
    """junction temperature of the worst-shared device after a single pulse of length t (current held constant)"""
    i_dev = i_total / v("n_fet") * v("share", case)
    tj = v("t_case", case)
    for _ in range(60):
        k = 1 + (v("rds_tc", case) - 1) * (tj - 25) / 100
        p = i_dev ** 2 * v("rds_25") * k
        tj_new = v("t_case", case) + p * zth(t, case)
        if tj_new > 400:
            return i_dev, p, float("inf")
        if abs(tj_new - tj) < 0.05:
            return i_dev, p, tj_new
        tj = tj_new
    return i_dev, p, tj


def fet_tmax(i_total, case):
    """longest single pulse keeping Tj <= tj_limit"""
    lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if fet_tj(i_total, mid, case)[2] <= v("tj_limit"):
            lo = mid
        else:
            hi = mid
    return lo


def fuse_i2t_pulse(i, t_on):
    return i * i * t_on


def report(md):
    L = []
    w = L.append
    w("# Calculation results (generated by `Calculations/Engineering_Models/weld_calc.py`)\n")
    w("> All values are **estimates** derived from the parameter table. None are measurements.\n")
    w("## 1. Parameters\n")
    w("| Key | min | typ | max | unit | origin |\n|---|---|---|---|---|---|")
    for k, (a, b, c, u, o) in P.items():
        w(f"| {k} | {a:g} | {b:g} | {c:g} | {u} | {o} |")

    w("\n## 2. Loop resistance budget (mOhm)\n")
    names = list(loop_resistances(1).keys())
    rr = [loop_resistances(i) for i in range(3)]
    w("| Element | best | typ | worst |\n|---|---|---|---|")
    for n in names:
        w(f"| {n} | {rr[0][n]*1e3:.2f} | {rr[1][n]*1e3:.2f} | {rr[2][n]*1e3:.2f} |")
    rext = [sum(r.values()) for r in rr]
    w(f"| **R_ext total** | **{rext[0]*1e3:.2f}** | **{rext[1]*1e3:.2f}** | **{rext[2]*1e3:.2f}** |")

    w("\n## 3. Weld current envelope\n")
    w("| Source | Case | R_source mOhm | R_ext mOhm | I_peak A | V_terminal during pulse V | P_weld-zone W | E_weld-zone in 10 ms J |")
    w("|---|---|---|---|---|---|---|---|")
    res = {}
    for label, rint_key, ocv_key in (("RT1270", "bat_rint", "bat_ocv"), ("Car battery (ref.)", "car_rint", "bat_ocv")):
        for case, cname, src_case in ((0, "best", 0), (1, "typ", 1), (2, "worst", 2)):
            rint = v(rint_key, src_case)
            ocv = v(ocv_key, 2 - src_case)
            re_ = rext[case]
            if label.startswith("Car"):
                # car battery would be used with a much lower-RDS stage; replace FET term by 1 mOhm
                re_ = re_ - rr[case]["MOSFETs (6x IRLZ44N, hot)"] + 0.001
            i, vt = current_envelope(rint, ocv, re_)
            pw = i * i * rr[case]["weld zone"]
            res[(label, cname)] = (i, vt, pw)
            w(f"| {label} | {cname} | {rint*1e3:.1f} | {re_*1e3:.2f} | {i:.0f} | {vt:.2f} | {pw:.0f} | {pw*0.01:.2f} |")
    i_typ = res[("RT1270", "typ")][0]
    i_best = res[("RT1270", "best")][0]
    i_car = res[("Car battery (ref.)", "typ")][0]
    p_ratio = res[("Car battery (ref.)", "typ")][2] / res[("RT1270", "typ")][2]
    w(f"\nRatio of weld-zone power car/RT1270 (typ): **{p_ratio:.1f}x**. "
      f"RT1270 typical current is **{i_typ/v('bat_imax_ds'):.1f}x** the datasheet 70 A (5 s) maximum.\n")

    w("\n## 4. MOSFET single-pulse stress (6x IRLZ44N, worst-shared device)\n")
    w("Zth(t) = RthJC*sqrt(t/tau) capped at RthJC (assumption). Current held constant (conservative).\n")
    w("| Total current A | Case | T_case C | I per device A | IDM margin | Tj after 20 ms | Tj after 50 ms | Tj after 100 ms | Max pulse for Tj<=150 C |")
    w("|---|---|---|---|---|---|---|---|---|")
    fmt = lambda x: "runaway" if x == float("inf") else f"{x:.0f} C"
    for itot in (200.0, i_typ, i_best, 450.0):
        for case, cname in ((0, "best"), (1, "typ"), (2, "worst")):
            r20 = fet_tj(itot, 0.02, case); r50 = fet_tj(itot, 0.05, case); r100 = fet_tj(itot, 0.1, case)
            tm = fet_tmax(itot, case)
            w(f"| {itot:.0f} | {cname} | {v('t_case',case):.0f} | {r20[0]:.0f} | {v('fet_idm')/r20[0]:.1f}x | {fmt(r20[2])} | {fmt(r50[2])} | {fmt(r100[2])} | {tm*1e3:.0f} ms |")
    w("\nConclusion basis: the firmware ON-time limit must stay below the 'typ' max-pulse column at the expected current.\n")

    w("\n## 5. Average dissipation (repetition)\n")
    idv, p, tj = fet_tj(i_typ, 0.05, 1)
    for period in (2.0, 5.0, 10.0):
        e = p * 0.065  # 50 ms main + 15 ms pre-pulse
        w(f"- One weld every {period:.0f} s, 65 ms total ON: {e:.1f} J/device/weld -> "
          f"{e/period:.1f} W/device, {6*e/period:.0f} W total into the drain busbar/heatsink.")

    w("\n## 6. Inductive energy at turn-off\n")
    for itot in (i_typ, i_best):
        e_w = 0.5 * v("l_weld", 2) * itot ** 2
        e_b = 0.5 * v("l_bat", 2) * itot ** 2
        w(f"- I = {itot:.0f} A: welding-cable energy {e_w*1e3:.0f} mJ (free-wheels through STPS3045CP), "
          f"battery-lead energy {e_b*1e3:.0f} mJ (absorbed by 1000 uF + SMBJ24CA at the assembly bus).")
    r_loop_fw = rr[1]["welding cables"] + rr[1]["electrode tips"] + rr[1]["weld zone"] + rr[1]["relay contacts"] + 4 * v("r_joint", 1)
    tau = v("l_weld", 2) / r_loop_fw
    i2t_fw = (i_best / 2) ** 2 * tau / 2
    w(f"- Free-wheel time constant ~{tau*1e3:.2f} ms; I2t per diode die (2 dice share) ~{i2t_fw:.1f} A2s "
      f"vs. 242 A2s for 220 A/10 ms half-sine (DS3 IFSM).")

    w("\n## 7. Control rail hold-up (diode-isolated banks)\n")
    v0 = v("bat_ocv", 0) - v("vf_supply", 2) - (v("i_logic", 2) + v("i_relay", 2)) * v("r_tap")
    w(f"Worst-case bank voltage before the pulse: {v0:.2f} V (OCV min - Vf max - I*R_tap).\n")
    w("| Rail | C used uF (min) | Load A (max) | ON time ms | Droop V | End voltage V | Limit |")
    w("|---|---|---|---|---|---|---|")
    for t in (65, int(round(pulse_limiter_window()[2]))):
        d = holdup(v("c_logic_uF", 0), v("i_logic", 2), t / 1e3)
        w(f"| Logic + gate drive | {v('c_logic_uF',0):.0f} | {v('i_logic',2)} | {t} | {d:.2f} | {v0-d:.2f} | UVLO {v('uvlo_th',2)} V, 7805 {v('v_7805_min_in')} V |")
        d = holdup(v("c_relay_uF", 0), v("i_relay", 2), t / 1e3)
        w(f"| Relay coil | {v('c_relay_uF',0):.0f} | {v('i_relay',2)} | {t} | {d:.2f} | {v0-d:.2f} | relay drop-out voltage UNKNOWN |")
    w("\n(65 ms = firmware maximum ON time: 50 ms main + 15 ms pre-pulse; second row = upper bound of the hardware limiter per ON interval.)\n")
    e_in = 0.5 * (v("c_logic_uF", 2) + v("c_relay_uF", 2)) * 1e-6 * v("bat_ocv", 2) ** 2
    i2t_in = v("bat_ocv", 2) ** 2 * (v("c_logic_uF", 2) + v("c_relay_uF", 2)) * 1e-6 / (2 * v("r_tap"))
    w(f"Inrush at connection: peak {v('bat_ocv',2)/v('r_tap'):.1f} A, energy in R_tap {e_in:.2f} J, "
      f"I2t {i2t_in:.2f} A2s (choose a T3.15 A fuse with I2t >> this value).\n")

    w("\n## 8. Hardware pulse-length limiter window (Monte-Carlo, 20 000 samples)\n")
    mn, md_, mx = pulse_limiter_window()
    w(f"R = 68 kOhm 1 %, C = 1 uF (-20/+10 %), Vth = VCC x 22k/(10k+22k), VCC 4.8-5.2 V, VOH VCC-0..0.2 V, LM393 Vos 5 mV.\n")
    w(f"- Hardware limit: min **{mn:.0f} ms**, median {md_:.0f} ms, max **{mx:.0f} ms**.")
    w(f"- Firmware limit per ON interval: {v('fw_max_on_ms'):.0f} ms -> margin to HW minimum {mn - v('fw_max_on_ms'):.0f} ms.")

    w("\n## 9. ADC scaling\n")
    for name, rt, rb in (("VBAT / VELEC / VDRV / VHOLD / VDRAIN", 33e3, 10e3),):
        k = (rt + rb) / rb
        w(f"- {name}: divider {rt/1e3:.0f}k/{rb/1e3:.0f}k, k = {k:.2f}; full scale {5*k:.1f} V at AVCC=5 V "
          f"({5*k/1024*1e3:.1f} mV/LSB), {1.1*k:.2f} V with the 1.1 V internal reference "
          f"({1.1*k/1024*1e3:.1f} mV/LSB); source impedance {rt*rb/(rt+rb)/1e3:.1f} kOhm.")
    w(f"- V_DS at typical current: {i_typ*(v('rds_25')*v('rds_tc',1)/6)*1e3:.0f} mV -> current estimate from V_DS has "
      "+-30 % uncertainty (RDS(T) spread). It is an indication, not a measurement.")

    w("\n## 10. Cable adiabatic short-circuit withstand\n")
    k = 115  # PHY  PVC-insulated copper; silicone cable is higher (k~141) - conservative
    for cs in (10, 16, 25):
        i2t = (k * cs) ** 2
        w(f"- {cs} mm2: I2t = {i2t/1e6:.2f} MA2s -> {i2t/i_best**2:.0f} s at {i_best:.0f} A")
    w(f"\nWeld-pulse I2t through the main fuse (best case {i_best:.0f} A, 65 ms): "
      f"{fuse_i2t_pulse(i_best,0.065)/1e3:.1f} kA2s per weld -> compare with the fuse's PRE-ARCING I2t "
      "(datasheet); require pre-arc I2t >= 5x pulse I2t to avoid fatigue.")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", help="write markdown report to this file")
    a = ap.parse_args()
    text = report(True)
    if a.md:
        with open(a.md, "w") as f:
            f.write(text + "\n")
    print(text)
