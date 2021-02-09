# -*- coding: utf-8 -*-

from lisp import *
from lisp import _eval, _repr


def test_lisp():
    x = eq('b', 'c')
    y = _eval(('eq', quote('b'), quote('c')))
    assert x == y == False

    x = quote('b')
    y = _eval(('quote', 'b'))
    assert _repr(x) == _repr(y) == 'b'

    x = cond((eq('b', 'b'), car(("xxx", "zzz"))), (True, "yyy"))
    assert _repr(x) == 'xxx'

    assert null('x') == False

    li = ("cond", (("eq", "b", "b"), ("car", ("quote", ("xxx", "zzz")))), (True, "yyy"))
    tokens = tokenize("(cond ((eq b b) ( car (quote (xxx zzz)))) (True yyy))")
    res = parse(tokens)
    assert res == li
    res = _eval(res)
    assert res == 'xxx'
    assert eq(car(('b', 'c')), 'c') is False
    assert cond((('eq', quote('b'), quote('c')), 'hello'), (True, 'world')) == _eval(
        ("cond", (("eq", "b", "c"), "hello"), (True, "world"))) == "world"
    assert cond((("eq", ("car", ("quote", ("c", "b"))), ("cdr", ("quote", (("a", "b"), "c")))), "c"), (True, "d")) == "c"
    assert ("a", "b", "c") == _eval(("quote", ("a", "b", "c")))
    assert and_(("eq", "a", "a"), True) is True
