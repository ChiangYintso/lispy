# -*- coding: utf-8 -*-
AtomSymbol = str
List = tuple


def _repr(s_expr):
    if isinstance(s_expr, bool):
        return repr(s_expr)
    return s_expr if atom(s_expr) else "(" + " ".join(_repr(i).strip("'") for i in s_expr) + ")"


def _to_py_proc(e):
    if isinstance(e, bool):
        return repr(e)
    if atom(e):
        return '()' if null(e) else f"'{_repr(e)}'"
    if e[0] == "quote":
        return f"quote({_to_py_proc(e[1]) if atom(e[1]) else repr(e[1])})"
    if e[0] == "cond":
        s = ""
        for (p, _e) in e[1:]:
            s += f"({_to_py_proc(p)}, {_to_py_proc(_e)}), "
        return f"cond({s})"
    return f"{e[0]}({', '.join(_to_py_proc(arg) for arg in e[1:])})"


def _eval(e):
    if isinstance(e, bool):
        return e
    py_proc = _to_py_proc(e)
    return eval(py_proc)


UNDEFINED = "undefined"
NIL = ()

atom = lambda x: isinstance(x, AtomSymbol) or x == NIL or isinstance(x, bool)
eq = lambda x, y: UNDEFINED if not atom(x) or not atom(y) else x == y
car = lambda x: UNDEFINED if atom(x) else x[0]
cdr = lambda x: UNDEFINED if atom(x) else x[1:]
cons = lambda x, y: (x, y)
quote = lambda x: x
cond = lambda *args: next((_eval(e) for (p, e) in args if isinstance(p, bool) and p or _eval(p)))

and_ = lambda p, q: cond((p, q), (True, False))
null = lambda x: and_(atom(x), eq(x, NIL))


def tokenize(s):
    start = 0
    for i in range(len(s)):
        if s[i] in "()'" or s[i].isspace():
            if start != i:
                yield eval(s[start:i]) if s[start:i] == "True" or s[start:i] == "False" else s[start:i]
            if s[i] in "()'":
                yield s[i]
            start = i + 1
    if start != len(s):
        yield eval(s[start:]) if s[start:] == "True" or s[start:] == "False" else s[start:]
    yield ""


def parse(tokens):
    """
    S-expr ::= ( S-expr* ) |  | ' S-expr
    ' S-expr = (quote S-expr)
    """
    from itertools import tee

    def _parse(tokens):
        while True:
            token = next(tokens)
            if token == "(":
                s_expr = []
                while True:
                    tokens, tokens_clone = tee(tokens)
                    if next(tokens_clone) == ")":
                        next(tokens)
                        return tuple(s_expr)
                    s_expr.append(_parse(tokens))
            elif token == ")" or token == "":
                raise Exception("parse error")
            elif token == "'":
                return "quote", _parse(tokens)
            else:
                return token

    s_expr = _parse(tokens)
    if next(tokens) != "":
        raise Exception("parse error")
    return s_expr


if __name__ == "__main__":
    while s := input(">>> "):
        tokens = tokenize(s)
        li = parse(tokens)
        print(_repr(_eval(li)))
