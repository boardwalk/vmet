#!/usr/bin/python3
import argparse
from collections import namedtuple

def is_white(ch):
    return ch in (" ", "\t", "\r", "\n")

def is_alpha(ch):
    return (ch >= "a" and ch <= "z") or (ch >= "A" and ch <= "Z") or ch == "_"

def is_num(ch):
    return ch >= "0" and ch <= "9"

class File(object):
    def __init__(self, f):
        self.f = f
        self.next()

    def last(self):
        return self.ch

    def next(self):
        self.ch = self.f.read(1)

Sym = namedtuple("Sym", ["val"])
StrLit = namedtuple("StrLit", ["val"])
IntLit = namedtuple("IntLit", ["val"])
FltLit = namedtuple("FltLit", ["val"])
Open = namedtuple("Open", [])
Close = namedtuple("Close", [])
EOF = namedtuple("EOF", [])

def next_token(f):
    while is_white(f.last()):
        f.next()

    if is_alpha(f.last()):
        sym = ""
        while is_alpha(f.last()):
            sym += f.last()
            f.next()
        return Sym(sym)

    if f.last() == "\"":
        f.next()
        lit = ""
        while f.last() != "\"":
            if f.last() == "":
                raise RuntimeError("unterminated string literal")
            lit += f.last()
            f.next()
        f.next()
        return StrLit(lit)

    if is_num(f.last()) or f.last() == "-":
        lit = f.last()
        f.next()
        while is_num(f.last()):
            lit += f.last()
            f.next()

        if f.last() != ".":
            return IntLit(int(lit))

        lit += f.last()
        f.next()
        while is_num(f.last()):
            lit += f.last()
            f.next()
        return FltLit(float(lit))

    if f.last() == "{":
        f.next()
        return Open()

    if f.last() == "}":
        f.next()
        return Close()

    if f.last() == "":
        return EOF()

    raise RuntimeError("bad input")

class Lexer(object):
    def __init__(self, f):
        self.f = f
        self.next()

    def last(self):
        return self.tok

    def next(self):
        self.tok = next_token(self.f)

def parse_single(l, ty):
    assert isinstance(l.last(), ty)
    val = l.last().val
    l.next()
    return val

def parse_sym(l):
    return parse_single(l, Sym)

def parse_str(l):
    return parse_single(l, StrLit)

def parse_int(l):
    return parse_single(l, IntLit)

def parse_flt(l):
    return parse_single(l, FltLit)

def parse_list(l, func):
    assert isinstance(l.last(), Open)
    l.next()

    res = []
    while not isinstance(l.last(), Close):
        res.append(func(l))

    l.next()
    return res

class Cond(object):
    def __init__(self, kind, *args):
        self.kind = kind
        self.args = args

class Action(object):
    def __init__(self, kind, *args):
        self.kind = kind
        self.args = args

class Table(object):
    def __init__(self, vals, cols=None):
        self.vals = vals
        self.cols = cols

Rule = namedtuple('Rule', ['state', 'cond', 'action'])

def parse_cond(l):
    kind = parse_sym(l)

    if kind == "never":
        return Cond(0, 0)

    if kind == "always":
        return Cond(1, 0)

    if kind == "all":
        return Cond(2, Table(parse_list(l, parse_cond)))

    if kind == "any":
        return Cond(3, Table(parse_list(l, parse_cond)))

    if kind == "chatMessage":
        return Cond(4, parse_str(l))

    if kind == "packSlotsLT":
        return Cond(5, parse_int(l))

    if kind == "secondsInStateGT":
        return Cond(6, parse_int(l))

    if kind == "navRouteEmpty":
        return Cond(7, 0)

    if kind == "characterDeath":
        return Cond(8, 0)

    if kind == "vendorOpen":
        return Cond(9, 0)

    if kind == "vendorClosed":
        return Cond(10, 0)

    if kind == "itemCountLE":
        return Cond(11, Table([parse_str(l), parse_int(l)], ["n", "c"]))

    if kind == "itemCountGE":
        return Cond(12, Table([parse_str(l), parse_int(l)], ["n", "c"]))

    # 13 monster name count within distance
    # 14 monster priority count within distance

    if kind == "needToBuff":
        return Cond(15, 0)

    # 16 no monsters within distance

    if kind == "landblockIs":
        return Cond(17, parse_int(l))

    if kind == "landcellIs":
        return Cond(18, parse_int(l))

    if kind == "portalSpaceEntered":
        return Cond(19, 0)

    if kind == "portalSpaceExited":
        return Cond(20, 0)

    if kind == "not":
        return Cond(21, Table([parse_cond(l)]))

    if kind == "secondsInStateGE":
        return Cond(22, parse_int(l))

    if kind == "timeLeftOnSpellGE":
        return Cond(23, Table([parse_int(l), parse_int(l)], ["sid", "sec"]))

    if kind == "burdenPercentGE":
        return Cond(24, parse_int(l))

    if kind == "distAnyRoutePtGE":
        return Cond(25, Table([parse_flt(l)], ["dist"]))

    if kind == "expr":
        return Cond(26, Table([parse_str(l)], ["e"]))

    # 27 ??

    if kind == "chatcap":
        return Cond(28, Table([parse_str(l), parse_str(l)], ["p", "c"]))

    raise RuntimeError("unknown condition kind")

def parse_action(l):
    if isinstance(l.last(), Open):
        return Action(3, Table(parse_list(l, parse_action)))

    assert isinstance(l.last(), Sym)
    kind = l.last().val
    l.next()

    if kind == "nothing":
        return Action(0, 0)

    if kind == "goto":
        return Action(1, parse_sym(l))

    if kind == "command":
        return Action(2, parse_str(l))

    # 4 load embedded nav root

    if kind == "call":
        return Action(5, Table([parse_sym(l), parse_sym(l)], ["st", "ret"]))

    if kind == "return":
        return Action(6, 0)

    if kind == "expract":
        return Action(7, Table([parse_str(l)], ["e"]))

    if kind == "exprchat":
        return Action(8, Table([parse_str(l)], ["e"]))

    if kind == "setWatchdog":
        return Action(9, Table([parse_sym(l), parse_flt(l), parse_flt(l)], ["s", "r", "t"]))

    if kind == "clearWatchdog":
        return Action(10, Table([], []))

    if kind == "get":
        return Action(11, Table([parse_sym(l), parse_sym(l)], ["o", "v"]))

    if kind == "set":
        return Action(12, Table([parse_sym(l), parse_sym(l)], ["o", "v"]))

    # 13 create view
    # 14 destroy view
    # 15 destroy all views

    raise RuntimeError("unknown action kind")

def parse_rule(lexer, state):
    cond = parse_cond(lexer)
    assert parse_sym(lexer) == "then"
    action = parse_action(lexer)
    return Rule(state, cond, action)

def parse_state(lexer):
    state = parse_sym(lexer)
    return parse_list(lexer, lambda lexer: parse_rule(lexer, state))

def parse_toplevel(lexer):
    rules = []
    while not isinstance(lexer.last(), EOF):
        rules.extend(parse_state(lexer))

    return rules

def write(x, f):
    if isinstance(x, Rule):
        write(x.cond.kind, f)
        write(x.action.kind, f)
        for a in x.cond.args:
            write(a, f)
        for a in x.action.args:
            write(a, f)
        write(x.state, f)
    elif isinstance(x, Cond):
        write(x.kind, f)
        for a in x.args:
            write(a, f)
    elif isinstance(x, Action):
        write(x.kind, f)
        for a in x.args:
            write(a, f)
    elif isinstance(x, int):
        f.write(b"i\r\n")
        f.write("{:d}".format(x).encode("utf8") + b"\r\n")
    elif isinstance(x, float):
        f.write(b"d\r\n")
        f.write("{:g}".format(x).encode("utf8") + b"\r\n")
    elif isinstance(x, str):
        f.write(b"s\r\n")
        f.write(x.encode("utf8") + b"\r\n")
    elif isinstance(x, Table):
        f.write(b"TABLE\r\n")
        f.write(b"2\r\n")
        if x.cols is None:
            f.write(b"K\r\n")
            f.write(b"V\r\n")
        else:
            f.write(b"k\r\n")
            f.write(b"v\r\n")
        f.write(b"n\r\n")
        f.write(b"n\r\n")
        f.write(str(len(x.vals)).encode("utf8") + b"\r\n")
        if x.cols is None:
            for val in x.vals:
                write(val, f)
        else:
            for col, val in zip(x.cols, x.vals):
                write(col, f)
                write(val, f)
    else:
        raise RuntimeError("unknown arg type")

def write_rules(rules, f):
    f.write(b"1\r\n")
    f.write(b"CondAct\r\n")
    f.write(b"5\r\n")
    f.write(b"CType\r\n")
    f.write(b"AType\r\n")
    f.write(b"CData\r\n")
    f.write(b"AData\r\n")
    f.write(b"State\r\n")
    f.write(b"n\r\n")
    f.write(b"n\r\n")
    f.write(b"n\r\n")
    f.write(b"n\r\n")
    f.write(b"n\r\n")
    f.write(str(len(rules)).encode("utf8") + b"\r\n")
    for r in rules:
        write(r, f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("rt"))
    parser.add_argument("output", type=argparse.FileType("wb"))
    args = parser.parse_args()
    l = Lexer(File(args.input))
    rules = parse_toplevel(l)
    write_rules(rules, args.output)

if __name__ == "__main__":
    main()
