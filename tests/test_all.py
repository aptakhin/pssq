import pytest

from pssq import Expr, Q


def test_expr():
    assert Expr(Expr.Arg, "a", 5).format(1) == ('"a"', "$1", (5,), 2)
    assert Expr(Expr.Arg, None, 'a!=5').format(1) == (None, 'a!=5', (), 2)
    assert Expr(Expr.Arg, "a=ANY({})", [2, 4]).format(1) == (None, 'a=ANY($1)', ([2, 4],), 2)
    assert Expr(Expr.Arg, "a<={}", 3).format(1) == (None, 'a<=$1', (3,), 2)
    assert Expr(Expr.Arg, "a", Q.any([1])).format(1) == ('"a"', "ANY($1)", ([1],), 2)
    assert Expr(Expr.Kwarg, "a", 5).format(1) == ('"a"', "$1", (5,), 2)
    assert Expr(Expr.Kwarg, "a", Q.any([1])).format(1) == ('"a"', "ANY($1)", ([1],), 2)


def test_all():
    assert Q.select().from_("foo").where(a=5).end() == ('SELECT * FROM "foo" WHERE "a"=$1', (5,))
    assert Q.select().from_("foo").where("a!=5").end() == ('SELECT * FROM "foo" WHERE a!=5', ())
    assert Q.select().from_("foo").where("a!=5").where("b!=7").end() == ('SELECT * FROM "foo" WHERE a!=5 AND b!=7', ())
    assert Q.select().from_("foo").where("a=ANY({})", [2, 4]).end() == ('SELECT * FROM "foo" WHERE a=ANY($1)', ([2, 4],))
    assert Q.select().from_("foo").where("a=ANY({})", [2, 4]).where("b={}", 3).end() == ('SELECT * FROM "foo" WHERE a=ANY($1) AND b=$2', ([2, 4], 3))
    assert Q.select().from_("foo").where("a<={}", 3).end() == ('SELECT * FROM "foo" WHERE a<=$1', (3,))
    assert Q.select("boo").from_("foo").where("a=5").end() == ('SELECT "boo" FROM "foo" WHERE a=5', ())
    assert Q.select(Q.unsafe("foo() AS qoo")).from_("foo").where(a=5).end() == ('SELECT foo() AS qoo FROM "foo" WHERE "a"=$1', (5,))
    assert Q.select([Q.unsafe("foo() AS qoo")]).from_("foo").where(a=5).end() == ('SELECT foo() AS qoo FROM "foo" WHERE "a"=$1', (5,))
    assert Q.select([Q.unsafe("foo() AS qoo"), "boolka"]).from_("foo").where(a=5).end() == ('SELECT foo() AS qoo,"boolka" FROM "foo" WHERE "a"=$1', (5,))

    assert Q.insert("foo").set_(a=5).end() == ('INSERT INTO "foo" ("a") VALUES ($1)', (5,))
    assert Q.insert("foo").set_(q=Q.unsafe("4"), w=Q.unsafe("now()"), a=5).end() == ('INSERT INTO "foo" ("q", "w", "a") VALUES (4, now(), $1)', (5,))

    assert Q.select().from_("foo").order("b").end() == ('SELECT * FROM "foo" ORDER BY "b"', ())
    assert Q.select().from_("foo").order("b", -1).end() == ('SELECT * FROM "foo" ORDER BY "b" DESC', ())

    assert Q.insert("foo").set_(a=5).returning("a").end() == ('INSERT INTO "foo" ("a") VALUES ($1) RETURNING "a"', (5,))

    assert Q.update("foo").set_(a=5, b=7).end() == ('UPDATE "foo" SET "a"=$1, "b"=$2', (5, 7))
    assert Q.update("foo").set_(a=5, b=7).where(a=2).end() == ('UPDATE "foo" SET "a"=$1, "b"=$2 WHERE "a"=$3', (5, 7, 2))
    assert Q.update("foo").set_(a=Q.unsafe("now()")).where(a=2).end() == ('UPDATE "foo" SET "a"=now() WHERE "a"=$1', (2,))

    assert Q.delete().from_("foo").end() == ('DELETE FROM "foo"', ())
    assert Q.delete().from_("foo").where(a=2).end() == ('DELETE FROM "foo" WHERE "a"=$1', (2,))


def test_python36plus():
    # Tests based on preserved order of kwargs are valid on Python 3.6+ only
    assert Q.insert("foo").set_(a=5, b=7).end() == ('INSERT INTO "foo" ("a", "b") VALUES ($1, $2)', (5, 7))


if __name__ == "__main__":
    pytest.main(["-s", "-x", __file__])
