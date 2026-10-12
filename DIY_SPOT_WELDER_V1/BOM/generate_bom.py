#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate BOM/MASTER_BOM.csv from KiCad/Generator/design.py (single source of truth)."""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "KiCad", "Generator"))
import design as D  # noqa: E402

COLS = ["Reference designator", "Quantity", "Description", "Manufacturer", "Manufacturer part number",
        "Electrical specifications", "Package / footprint", "Available in my inventory", "Needs purchasing",
        "Estimated price (EUR, each)", "Datasheet URL", "Verification status", "Engineering notes"]

INV = {"STOCK": ("YES", "NO"), "PURCHASE": ("NO", "YES"), "UNVERIFIED": ("PARTLY / UNKNOWN", "IF NOT IN STOCK"),
       "REJECTED": ("YES", "NO")}


def natkey(ref):
    import re
    m = re.match(r"([A-Za-z#]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def main():
    groups = {}
    for c in D.COMPONENTS:
        if c["sym"].startswith("power:") or c["ref"].startswith("#"):
            continue
        fp = c["fp"].split(":", 1)[1] if c["fp"] else ("off-board: POWER ASSEMBLY" if not c["on_board"] else "")
        key = (c["value"], fp, c["mpn"], c["status"], c["desc"], c["on_board"])
        groups.setdefault(key, []).append(c)
    rows = []
    for key, cs in groups.items():
        c = cs[0]
        refs = sorted((x["ref"] for x in cs), key=natkey)
        inv, buy = INV.get(c["status"], ("?", "?"))
        notes = c["notes"]
        if not c["on_board"]:
            notes = ("[POWER ASSEMBLY, not on PCB] " + notes).strip()
        rows.append([" ".join(refs), len(refs), c["desc"], c["mfr"], c["mpn"] or c["value"], c["spec"], key[1], inv, buy,
                     c["price"], c["ds"], c["status"], notes])
    for ref, qty, desc, mfr, mpn, spec, pkg, status, price, ds, notes in D.BOM_EXTRA:
        inv, buy = INV.get(status, ("?", "?"))
        rows.append([ref, qty, desc, mfr, mpn, spec, pkg, inv, buy, price, ds, status, notes])
    for ref, qty, desc, mfr, mpn, spec, pkg, status, price, ds, notes in D.BOM_NOT_USED:
        inv = "YES"
        rows.append([ref, qty, desc, mfr, mpn, spec, pkg, inv, "NO", price, ds, status, "[NOT USED IN V1] " + notes])
    order = {"STOCK": 0, "UNVERIFIED": 1, "PURCHASE": 2, "REJECTED": 3}
    rows.sort(key=lambda r: (r[11] == "REJECTED" or r[12].startswith("[NOT USED"), natkey(r[0].split()[0])))
    out = os.path.join(HERE, "MASTER_BOM.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(rows)
    # summary
    cnt = {}
    for r in rows:
        cnt[r[11]] = cnt.get(r[11], 0) + 1
    print(f"wrote {out}: {len(rows)} lines", cnt)


if __name__ == "__main__":
    main()
