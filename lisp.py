# -*- coding: utf-8 -*-
AtomSymbol = str
SList = tuple


def UNDEFINED(s):
    raise Exception(f"undefined: {s}")


NIL = ()


def _repr(s_expr):
    if isinstance(s_expr, bool):
        return repr(s_expr)
    if s_expr == NIL:
        return '()'
    return s_expr if atom(s_expr) else "(" + " ".join(_repr(i).strip("'") for i in s_expr) + ")"


def _to_py_proc(e, env=None):
    """
    >>> _to_py_proc(("defn", "null", ("x", ), ("and_", ("atom", "x"), ("eq", "x", NIL))))
    "defn('null', ('x',), ('and_', ('atom', 'x'), ('eq', 'x', ())))"
    """

    def lazy_eval(e, env):
        return _to_py_proc(e, env) if atom(e) else repr(e)

    if env is None:
        env = {}
    env = {NIL, *elem_fn_table.keys(), *env}

    if isinstance(e, bool):
        return repr(e)
    if atom(e):
        if e == NIL:
            return '()'
        # fn as argument
        if (li := elem_fn_table.get(e)) is not None or (li := defn_table.get(e)) is not None:
            assert li[0] == "label"
            return f"quote({repr(li)})"
        return e if e in env else f"'{e}'"
    if e[0] == "quote":
        return f"quote({lazy_eval(e[1], env)})"
    if e[0] == "defn":
        return f"{e[0]}{lazy_eval(e[1:], {*e[2], *env})}"
    if e[0] == "cond":
        s = "".join(f"({lazy_eval(p, env)}, {lazy_eval(_e, env)}), " for (p, _e) in e[1:])
        return f"cond({s})"
    # define fn
    if e[0] == "label":
        assert len(e) == 3
        assert isinstance(e[1], AtomSymbol)
        elem_fn_table[e[1]] = e
        return repr(e)
    if e[0] == "lambda":
        return repr(e)

    def _get_fn(e):
        if e in elem_fn_table:
            return e
        if isinstance(e, SList):
            # (label eqq (lambda (x y) (eq x y)) 
            if e[0] == "label":
                assert len(e) == 3
                defn_table[e[1]] = e[2]
                defn(e[1], e[2][1], e[2][2])
                return e[1]
            # (lambda (x y) (eq x y)
            assert isinstance(e, SList) and e[0] == "lambda"
            return f"(lambda {', '.join(e[1])}: {_to_py_proc(e[2], env=e[1])})"
        return e

    return f"{_get_fn(e[0])}({', '.join(_to_py_proc(arg, env) for arg in e[1:])})"


atom = lambda x: isinstance(x, AtomSymbol) or x == NIL or isinstance(x, bool)
eq = lambda x, y: UNDEFINED("eq") if not atom(x) or not atom(y) else x == y
car = lambda x: UNDEFINED("car") if atom(x) else x[0]
cdr = lambda x: UNDEFINED("cdr") if atom(x) else x[1:]
cons = lambda x, y: (x, y)
quote = lambda x: x


def cond(*args):
    for (p, e) in args:
        if isinstance(p, bool) and p or not isinstance(p, bool) and py_eval(p):
            return py_eval(e)
    UNDEFINED("cond")


def defn(fn_name: AtomSymbol, args: SList, e):
    if fn_name in elem_fn_table:
        raise Exception("can not modify elementary fn")

    defn_table[fn_name] = ("label", fn_name, ("lambda", args, e))
    exec(f"{fn_name} = lambda {', '.join(args)}: {_to_py_proc(e, env={fn_name, *args})}", globals())
    return defn_table[fn_name]


def py_eval(e):
    py_proc = _to_py_proc(e)
    return eval(py_proc)


def load(e: AtomSymbol):
    """
    :example:
        (load ./foo.lisp)
    """
    try:
        with open(e) as f:
            lisp_code = " ".join(f.readlines())
            interpret(lisp_code)
    except (FileExistsError, FileNotFoundError):
        print(f"[err] can not find {e}")


elem_fn_table = {
    "atom": ("label", "atom", ("lambda", ("x",), NIL)),
    "eq": ("label", "eq", ("lambda", ("x", "y"), NIL)),
    "car": ("label", "car", ("lambda", ("x",), NIL)),
    "cdr": ("label", "cdr", ("lambda", ("x",), NIL)),
    "cons": ("label", "cons", ("lambda", ("x", "y"), NIL)),
    "quote": ("label", "quote", ("lambda", ("x",), NIL)),
    "cond": ("label", "cond", ("lambda", ("*args",), NIL)),
    "defn": ("label", "defn", ("lambda", ("fn_name", "args", "e"), NIL)),
    "py_eval": ("label", "py_eval", ("lambda", ("e",), NIL)),
    "load": ("label", "load", ("lambda", ("e",), NIL)),

}

defn_table = {
    "and_": ("label", "and_", ("lambda", ("p", "q"), ("cond", ("p", "q"), (True, False))))
}

# equaling to `defn("and_", ("p", "q"), ("cond", ("p", "q"), (True, False)))`
and_ = lambda p, q: cond((p, q), (True, False))

# equaling to `or_ = lambda p, q: cond((p, True), (q, True), (True, False))`
defn("or_", ("p", "q"), ("cond", ("p", True), ("q", True), (True, False)))

# equaling to `null = lambda x: and_(atom(x), eq(x, NIL))`
# defn("null", ("x",), ("and_", ("atom", "x"), ("eq", "x", NIL)))
py_eval(("defn", "null", ("x",), ("and_", ("atom", "x"), ("eq", "x", NIL))))


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
    S-expr ::= ( S-expr* ) | AtomSymbol | ' S-expr
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


def interpret(s: str):
    try:
        tokens = tokenize(s)
        li = parse(tokens)
        res = py_eval(li)
        if res is not None:
            print(_repr(res))
    except:
        traceback.print_exc()


if __name__ == "__main__":
    import traceback

    load("lib.lisp")
    while s := input(">>> "):
        interpret(s)
