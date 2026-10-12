# SPDX-License-Identifier: GPL-3.0-or-later
"""
Connectivity / rule check of the generated schematic.

THIS IS NOT KiCad ERC. KiCad 7.0 kicad-cli has no 'sch erc' command; KiCad 10 ERC must be run
locally (command in README.md). This script performs:

 1. PARITY: KiCad's own netlist export (kicad-cli sch export netlist) is compared against the
    intended connectivity in design.py -> proves the drawn schematic equals the design intent.
 2. RULES on the full design (incl. off-board parts and PWR_FLAGs) using symbol pin types:
    unassigned pins, single-pin nets, undriven power inputs, multiple drivers, undriven inputs.

Usage: python3 check_schematic.py <exported.net> <report.txt>
"""
import sys
from collections import defaultdict

from sexpr import parse, find, find1
from symlib import SymLib, pins as sym_pins
import design as D

SL = SymLib()


def load_netlist(path):
    t = parse(open(path, encoding="utf-8").read())[0]
    nets = {}
    for n in find(find1(t, "nets"), "net"):
        name = str(find1(n, "name")[1])
        short = name.split("/")[-1] if name.startswith("/") else name
        nodes = [(str(find1(x, "ref")[1]), str(find1(x, "pin")[1]), str(find1(x, "pintype")[1]) if find1(x, "pintype") else "")
                 for x in find(n, "node")]
        nets[short] = nodes
    comps = {str(find1(c, "ref")[1]) for c in find(find1(t, "components"), "comp")}
    return nets, comps


def intended():
    conn = defaultdict(set)
    for c in D.COMPONENTS:
        if not c["on_board"] or c["sym"].startswith("power:"):
            continue
        for pin, net in c["pins"].items():
            if net:
                conn[net].add((c["ref"], pin))
    return conn


def main(netfile, report):
    out = []
    w = out.append
    errors = warnings = 0
    nets, comps = load_netlist(netfile)
    want = intended()
    w("DIY_SPOT_WELDER_V1 - schematic connectivity check (custom script, NOT KiCad ERC)")
    w(f"Netlist: {netfile}")
    w("")
    w("[1] Parity: kicad-cli exported netlist vs. design.py (on-board parts)")
    got = {n: {(r, p) for r, p, _ in nodes} for n, nodes in nets.items()}
    # drop NC single nodes that KiCad exports as unconnected-(...) nets
    got = {n: s for n, s in got.items() if not n.startswith("unconnected-")}
    names = set(got) | set(want)
    for n in sorted(names):
        a, b = got.get(n, set()), want.get(n, set())
        if a != b:
            errors += 1
            w(f"  ERROR net {n}: only in schematic {sorted(a - b)}, only in design {sorted(b - a)}")
    want_refs = {c["ref"] for c in D.COMPONENTS if c["on_board"] and not c["sym"].startswith("power:")}
    if want_refs != comps:
        errors += 1
        w(f"  ERROR component set differs: missing {sorted(want_refs - comps)}, extra {sorted(comps - want_refs)}")
    w(f"  nets compared: {len(names)}, on-board components: {len(comps)}")
    w("  RESULT: " + ("PASS" if errors == 0 else f"{errors} ERROR(S)"))
    w("")
    w("[2] Rule checks on the full design (incl. off-board power assembly and PWR_FLAGs)")
    netpins = defaultdict(list)
    for c in D.COMPONENTS:
        try:
            s = SL.get(*c["sym"].split(":"))
        except KeyError:
            w(f"  ERROR symbol not found {c['sym']}"); errors += 1; continue
        plist = sym_pins(s)
        numbers = {p["number"] for p in plist}
        for p in plist:
            if p["number"] not in c["pins"]:
                if p["hidden"] and p["type"] == "no_connect":
                    continue
                w(f"  ERROR {c['ref']} pin {p['number']} ({p['name']}) not assigned"); errors += 1
        for num, net in c["pins"].items():
            if num not in numbers:
                w(f"  ERROR {c['ref']} pin {num} does not exist in symbol {c['sym']}"); errors += 1
                continue
            if net is None:
                continue
            ptype = next(p["type"] for p in plist if p["number"] == num)
            netpins[net].append((c["ref"], num, ptype))
    for net, ps in sorted(netpins.items()):
        types = [t for _, _, t in ps]
        refs = {r for r, _, _ in ps}
        if len(ps) == 1 or (len(refs) == 1 and not any(r.startswith("#") for r in refs) and len(ps) > 1 and len(set(n for _, n, _ in ps)) == len(ps) and False):
            w(f"  WARNING single-pin net {net}: {ps}"); warnings += 1
        drivers = [t for t in types if t in ("output", "power_out")]
        if len(drivers) > 1:
            w(f"  ERROR multiple drivers on {net}: {ps}"); errors += 1
        if "power_in" in types and not any(t == "power_out" for t in types):
            w(f"  ERROR power input(s) on {net} not driven by power_out/PWR_FLAG: {[p for p in ps if p[2]=='power_in']}"); errors += 1
        if "input" in types and not any(t in ("output", "power_out", "bidirectional", "passive", "open_collector", "tri_state") for t in types):
            w(f"  ERROR inputs on {net} have no driver: {ps}"); errors += 1
        if "open_collector" in types and "output" in types:
            w(f"  WARNING open-collector and push-pull output share {net}"); warnings += 1
    w(f"  nets checked: {len(netpins)}")
    w("")
    w(f"SUMMARY: {errors} error(s), {warnings} warning(s)")
    w("Note: a clean result proves netlist consistency only - it is NOT an electrical or safety approval.")
    txt = "\n".join(out) + "\n"
    open(report, "w").write(txt)
    print(txt)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
