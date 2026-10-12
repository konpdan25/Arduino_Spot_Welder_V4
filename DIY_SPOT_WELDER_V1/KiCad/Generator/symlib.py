# SPDX-License-Identifier: GPL-3.0-or-later
"""Load KiCad .kicad_sym libraries, flatten 'extends', extract pins (DIY_SPOT_WELDER_V1 generator)."""
import copy
import os
from sexpr import parse, find, find1, Q

KICAD_SYMBOL_DIR = os.environ.get("KICAD7_SYMBOL_DIR", "/usr/share/kicad/symbols")


class SymLib:
    def __init__(self, sym_dir=KICAD_SYMBOL_DIR):
        self.dir = sym_dir
        self.cache = {}

    def _lib(self, lib):
        if lib not in self.cache:
            tree = parse(open(os.path.join(self.dir, lib + ".kicad_sym"), encoding="utf-8").read())[0]
            self.cache[lib] = {s[1]: s for s in find(tree, "symbol")}
        return self.cache[lib]

    def get(self, lib, name):
        """Return a flattened top-level symbol node named `name` (no library prefix)."""
        syms = self._lib(lib)
        s = copy.deepcopy(syms[name])
        ext = find1(s, "extends")
        if ext is None:
            return s
        parent = self.get(lib, ext[1])
        pname = parent[1]
        out = [x for x in parent if not (isinstance(x, list) and x[0] == "property")]
        out[1] = Q(name)
        # child properties replace the parent's
        props = [x for x in s if isinstance(x, list) and x[0] == "property"]
        pos = 2
        for p in props:
            out.insert(pos, p)
            pos += 1
        # rename unit sub-symbols
        for sub in find(out, "symbol"):
            sub[1] = Q(sub[1].replace(pname, name, 1))
        # inherit flags of child (in_bom/on_board) if present
        return out


def prop(sym, key):
    for p in find(sym, "property"):
        if p[1] == key:
            return p[2]
    return None


def pins(sym):
    """List of dict(number, name, type, x, y, angle, length, unit, hidden) - lib coordinates (y up)."""
    out = []
    for sub in find(sym, "symbol"):
        # sub-symbol name: NAME_unit_style
        parts = sub[1].rsplit("_", 2)
        unit = int(parts[-2])
        for p in find(sub, "pin"):
            at = find1(p, "at")
            num = find1(p, "number")[1]
            nm = find1(p, "name")[1]
            length = float(find1(p, "length")[1])
            hidden = "hide" in p
            out.append(dict(number=str(num), name=str(nm), type=p[1], gfx=p[2],
                            x=float(at[1]), y=float(at[2]), angle=float(at[3]) if len(at) > 3 else 0.0,
                            length=length, unit=unit, hidden=hidden))
    return out


def unit_count(sym):
    units = set()
    for sub in find(sym, "symbol"):
        units.add(int(sub[1].rsplit("_", 2)[-2]))
    units.discard(0)
    return max(units) if units else 1


def body_bbox(sym, unit):
    """Rough bounding box (lib coords) of graphics + pin endpoints for a unit (unit 0 = common)."""
    xs, ys = [], []
    for sub in find(sym, "symbol"):
        u = int(sub[1].rsplit("_", 2)[-2])
        if u not in (0, unit):
            continue
        for g in sub:
            if not isinstance(g, list):
                continue
            if g[0] == "rectangle":
                for k in ("start", "end"):
                    n = find1(g, k); xs.append(float(n[1])); ys.append(float(n[2]))
            elif g[0] in ("polyline",):
                for xy in find(find1(g, "pts"), "xy"):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
            elif g[0] == "circle":
                c = find1(g, "center"); r = float(find1(g, "radius")[1])
                xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
            elif g[0] == "pin":
                at = find1(g, "at"); xs.append(float(at[1])); ys.append(float(at[2]))
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))


if __name__ == "__main__":
    import sys
    L = SymLib()
    for arg in sys.argv[1:]:
        lib, name = arg.split(":")
        s = L.get(lib, name)
        print(f"== {arg}  units={unit_count(s)}  fp={prop(s,'Footprint')!r}")
        for p in sorted(pins(s), key=lambda p: (p['unit'], p['number'].zfill(3))):
            print(f"   u{p['unit']} pin {p['number']:>3} {p['name']:<14} {p['type']:<14} at ({p['x']},{p['y']},{p['angle']:.0f}) {'HIDDEN' if p['hidden'] else ''}")
