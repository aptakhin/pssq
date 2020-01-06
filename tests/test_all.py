import pytest

from pssq import Expr, Q


def test_expr():
    assert Expr(Expr.Arg, "a", 5).format(1) == ('"a"', "$1", (5,), 2)
    assert Expr(Expr.Arg, None, 'a!=5').format(1) == (None, 'a!=5', (), 2)
    assert Expr(Expr.Arg, "a=ANY({})", [2, 4]).format(1) == (None, 'a=ANY($1)', ([2, 4],), 2)
    assert Expr(Expr.Arg, "a<={}", 3).format(1) == (None, 'a<=$1', (3,), 2)
    assert Expr(Expr.Arg, "a", Q.Any([1])).format(1) == ('"a"', "ANY($1)", ([1],), 2)
    assert Expr(Expr.Kwarg, "a", 5).format(1) == ('"a"', "$1", (5,), 2)
    assert Expr(Expr.Kwarg, "a", Q.Any([1])).format(1) == ('"a"', "ANY($1)", ([1],), 2)


def test_all():
    assert Q.SELECT().FROM("foo").WHERE(a=5).END() == ('SELECT * FROM "foo" WHERE "a"=$1', (5,))
    assert Q.SELECT().FROM("foo").WHERE("a!=5").END() == ('SELECT * FROM "foo" WHERE a!=5', ())
    assert Q.SELECT().FROM("foo").WHERE("a!=5").WHERE("b!=7").END() == ('SELECT * FROM "foo" WHERE a!=5 AND b!=7', ())
    assert Q.SELECT().FROM("foo").WHERE("a=ANY({})", [2, 4]).END() == ('SELECT * FROM "foo" WHERE a=ANY($1)', ([2, 4],))
    assert Q.SELECT().FROM("foo").WHERE("a=ANY({})", [2, 4]).WHERE("b={}", 3).END() == ('SELECT * FROM "foo" WHERE a=ANY($1) AND b=$2', ([2, 4], 3))
    assert Q.SELECT().FROM("foo").WHERE("a<={}", 3).END() == ('SELECT * FROM "foo" WHERE a<=$1', (3,))
    assert Q.SELECT("boo").FROM("foo").WHERE("a=5").END() == ('SELECT "boo" FROM "foo" WHERE a=5', ())
    assert Q.SELECT(Q.Unsafe("foo() as qoo")).FROM("foo").WHERE(a=5).END() == ('SELECT foo() as qoo FROM "foo" WHERE "a"=$1', (5,))
    assert Q.SELECT([Q.Unsafe("foo() as qoo")]).FROM("foo").WHERE(a=5).END() == ('SELECT foo() as qoo FROM "foo" WHERE "a"=$1', (5,))
    assert Q.SELECT([Q.Unsafe("foo() as qoo"), "boolka"]).FROM("foo").WHERE(a=5).END() == ('SELECT foo() as qoo,"boolka" FROM "foo" WHERE "a"=$1', (5,))

    assert Q.INSERT("foo").SET(a=5).END() == ('INSERT INTO "foo" ("a") VALUES ($1)', (5,))
    assert Q.INSERT("foo").SET(q=Q.Unsafe("4"), w=Q.Unsafe("now()"), a=5).END() == ('INSERT INTO "foo" ("q", "w", "a") VALUES (4, now(), $1)', (5,))

    assert Q.SELECT().FROM("foo").ORDER("b").END() == ('SELECT * FROM "foo" ORDER BY "b"', ())
    assert Q.SELECT().FROM("foo").ORDER("b", -1).END() == ('SELECT * FROM "foo" ORDER BY "b" DESC', ())

    assert Q.INSERT("foo").SET(a=5).RETURNING("a").END() == ('INSERT INTO "foo" ("a") VALUES ($1) RETURNING "a"', (5,))

    assert Q.UPDATE("foo").SET(a=5, b=7).END() == ('UPDATE "foo" SET "a"=$1, "b"=$2', (5, 7))
    assert Q.UPDATE("foo").SET(a=5, b=7).WHERE(a=2).END() == ('UPDATE "foo" SET "a"=$1, "b"=$2 WHERE "a"=$3', (5, 7, 2))
    assert Q.UPDATE("foo").SET(a=Q.Unsafe("now()")).WHERE(a=2).END() == ('UPDATE "foo" SET "a"=now() WHERE "a"=$1', (2,))

    assert Q.DELETE("foo").END() == ('DELETE "foo"', ())
    assert Q.DELETE("foo").WHERE(a=2).END() == ('DELETE "foo" WHERE "a"=$1', (2,))


def test_python36plus():
    # Tests based on preserved order of kwargs are valid on Python 3.6+ only
    assert Q.INSERT("foo").SET(a=5, b=7).END() == ('INSERT INTO "foo" ("a", "b") VALUES ($1, $2)', (5, 7))


if __name__ == "__main__":
    pytest.main(["-s", "-x", __file__])
