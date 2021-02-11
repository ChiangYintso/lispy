# -*- coding: utf-8 -*-
import traceback

AtomSymbol = str
SList = tuple

UNDEFINED = None
NIL = ()


def _repr(s_expr):
    if isinstance(s_expr, bool):
        return repr(s_expr)
    if s_expr == NIL:
        return '()'
    return s_expr if atom(s_expr) else "(" + " ".join(_repr(i).strip("'") for i in s_expr) + ")"


def _to_py_proc(e, env=None, expand_fn=True, lazy=False):
    """
    >>> _to_py_proc(("defn", "null", ("x", ), ("and_", ("atom", "x"), ("eq", "x", NIL))))
    "defn('null', ('x'), ('and_', ('atom', 'x'), ('eq', 'x', ())))"
    """

    if env is None:
        env = {}
    env = {NIL, *elem_fn_table.keys(), *env}

    if isinstance(e, bool):
        return repr(e)
    if e == NIL:
        return '()'
    if atom(e):
        # fn as argument
        if (li := elem_fn_table.get(e)) is not None or (li := defn_table.get(e)) is not None:
            assert li[0] == "label"
            return f"quote({repr(li)})" if expand_fn else f"'{e}'"
        return e if e in env else f"'{e}'"

    def _lazy_list(e):
        return f"({', '.join(_to_py_proc(elem, env, expand_fn=False, lazy=True) for elem in e)})"

    if lazy:
        return _lazy_list(e)

    if e[0] == "quote":
        return f"quote({_to_py_proc(e[1], env, lazy=True)})"
    if e[0] == "defn":
        return f"defn{_lazy_list(e[1:])}"
    if e[0] == "cond":
        s = "".join(
            f"({_to_py_proc(p, env, expand_fn=False, lazy=True)}, {_to_py_proc(_e, env, expand_fn=False, lazy=True)}), "
            for (p, _e) in e[1:])
        return f"cond({s})"

    # define fn
    if e[0] == "label":
        assert len(e) == 3
        assert isinstance(e[1], AtomSymbol)
        defn_table[e[1]] = e
        return _lazy_list(e)
    if e[0] == "lambda":
        return _lazy_list(e)

    def _get_fn(e):
        if isinstance(e, SList):
            # (label eqq (lambda (x y) (eq x y)) 
            if e[0] == "label":
                assert len(e) == 3
                if e[1] in elem_fn_table:
                    return e[1]
                defn_table[e[1]] = e[2]
                defn(e[1], e[2][1], e[2][2])
                return e[1]
            # (lambda (x y) (eq x y)
            assert isinstance(e, SList) and e[0] == "lambda"
            return f"(lambda {', '.join(e[1])}: {_to_py_proc(e[2], env=e[1])})"
        return e

    return f"{_get_fn(e[0])}({', '.join(_to_py_proc(arg, env) for arg in e[1:])})"


atom = lambda x: isinstance(x, AtomSymbol) or x == NIL or isinstance(x, bool)
eq = lambda x, y: UNDEFINED if not atom(x) or not atom(y) else x == y
car = lambda x: UNDEFINED if atom(x) else x[0]
cdr = lambda x: UNDEFINED if atom(x) else x[1:]
cons = lambda x, y: (x, y)
quote = lambda x: x


def cond(*args):
    for (p, e) in args:
        if isinstance(p, bool) and p or not isinstance(p, bool) and py_eval(p):
            return py_eval(e)
    return UNDEFINED


def defn(fn_name: AtomSymbol, args: SList, e):
    if fn_name in elem_fn_table:
        raise Exception("can not redefine elementary fn")

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
            lines = f.readlines()
            count = 0
            lisp_code = ""
            for line in lines:
                if len(line) == 0 or line.isspace():
                    continue
                for c in line:
                    if c == "(":
                        count += 1
                    elif c == ")":
                        count -= 1
                        if count < 0:
                            print('err in parsing')
                    elif count == 0 and not c.isspace():
                        print("err in parsing")
                        return
                lisp_code += line
                if count == 0:
                    interpret(lisp_code)
                    lisp_code = ""
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
# and_ = lambda p, q: cond((p, q), (True, False))
py_eval(("defn", "and_", ("p", "q"), ("cond", ("p", "q"), (True, False))))

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
    load("lib.lisp")

    while s := input(">>> "):
        interpret(s)
