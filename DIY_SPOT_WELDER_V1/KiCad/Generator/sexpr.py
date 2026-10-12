# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal S-expression reader/writer for KiCad files (DIY_SPOT_WELDER_V1 generator)."""
import re

_TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


class Q(str):
    """A string that must be written quoted."""


def parse(text):
    stack = [[]]
    for m in _TOK.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            last = stack.pop()
            stack[-1].append(last)
        elif t.startswith('"'):
            stack[-1].append(Q(t[1:-1].replace('\\"', '"').replace('\\\\', '\\')))
        else:
            stack[-1].append(t)
    return stack[0]


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(a, float):
        s = ('%.4f' % a).rstrip('0').rstrip('.')
        return s if s not in ('-0', '') else '0'
    return str(a)


def dumps(node, indent=0):
    """Pretty print with KiCad-like layout (one sub-list per line for long nodes)."""
    if not isinstance(node, list):
        return _atom(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple or (len(node) <= 4 and all(not isinstance(c, list) or all(not isinstance(x, list) for x in c) for c in node) and len(str(node)) < 90):
        return '(' + ' '.join(dumps(c) for c in node) + ')'
    out = '('
    first = True
    for c in node:
        if isinstance(c, list):
            out += '\n' + '  ' * (indent + 1) + dumps(c, indent + 1)
        else:
            out += ('' if first else ' ') + _atom(c)
        first = False
    out += '\n' + '  ' * indent + ')'
    return out


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None
