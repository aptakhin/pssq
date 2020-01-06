
def quoted(s):
    return '"%s"' % s


class _Unsafe:
    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return "Q.Unsafe(%s)" % repr(self.value)


class _Any:
    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return "Q.Any(%s)" % repr(self.value)


class Expr:
    Arg = "arg"
    Kwarg = "kwarg"

    def __init__(self, tp, key, value=None):
        self.tp = tp
        self.key = key
        self.value = value

    def format(self, idx):
        if self.tp == self.Arg:
            if self.key and "{}" in self.key:
                insert = None
                key = self.key.replace("{}", "$%d" % idx)
                value = (self.value,) if self.key is not None else ()
                idx += 1
            elif isinstance(self.value, _Any):
                insert = quoted(self.key)
                key = "ANY($%d)" % idx
                value = (self.value.value,)
                idx += 1
            else:
                insert = quoted(self.key) if self.key is not None else None
                key = "$%d" % idx if self.key is not None else self.value
                value = (self.value,) if self.key is not None else ()
                idx += 1

            res = insert, key, value, idx
        elif self.tp == self.Kwarg:
            insert = quoted(self.key) if self.key is not None else None
            if isinstance(self.value, _Unsafe):
                key = str(self.value)
                value = ()
            elif isinstance(self.value, _Any):
                key = "ANY($%d)" % idx
                value = (self.value.value,)
                idx += 1
            else:
                key = "$%d" % idx if self.key is not None else self.value
                value = (self.value,) if self.key is not None else ()
                idx += 1

            res = insert, key, value, idx

        # print(res)
        return res

    def __repr__(self):
        return 'Expr(%s, %s, %s)' % (repr(self.tp), repr(self.key), repr(self.value))


class Q:
    Unsafe = _Unsafe
    Any = _Any

    _M_SELECT = "SELECT"
    _M_INSERT = "INSERT"
    _M_UPDATE = "UPDATE"
    _M_DELETE = "DELETE"

    @staticmethod
    def SELECT(fields=None):
        q = Q(main_cmd=Q._M_SELECT)
        if fields is None:
            fields = "*"
        elif isinstance(fields, str):
            fields = [f.strip() for f in fields.split(",")]

        if fields != "*" and not isinstance(fields, list):
            fields = [fields]

        q.select_fields = fields
        return q

    @staticmethod
    def INSERT(table):
        q = Q(main_cmd=Q._M_INSERT)
        q._INSERT_TO = table
        return q

    @staticmethod
    def UPDATE(table):
        q = Q(main_cmd=Q._M_UPDATE)
        q._UPDATE = table
        return q

    @staticmethod
    def DELETE(table):
        q = Q(main_cmd=Q._M_DELETE)
        q._DELETE = table
        return q

    def __init__(self, main_cmd=None):
        self.main_cmd = main_cmd
        assert main_cmd in (None, Q._M_SELECT, Q._M_INSERT, Q._M_UPDATE, Q._M_DELETE)
        self.select_fields = None
        self.update_fields = None

        self._FROM = None
        self._INSERT_TO = None
        self._UPDATE = None
        self._DELETE = None

        self._WHERE = []
        self._SET = []
        self._ORDER = []
        self._RETURNING = []
        self._ON_CONFLICT_DO_NOTHING = None

    def FROM(self, table):
        self._FROM = table
        return self

    def WHERE(self, *args, **kwargs):
        if args and kwargs:
            raise RuntimeError("Can't understand args and kwargs in WHERE")
        if args:
            key = args[0] if len(args) > 1 else None
            value = args[1] if len(args) > 1 else args[0]
            self._WHERE.append(Expr(Expr.Arg, key, value))
        for key, value in kwargs.items():
            self._WHERE.append(Expr(Expr.Kwarg, key, value))
        return self

    def SET(self, *args, **kwargs):
        if args:
            key = args[0] if len(args) > 1 else None
            value = args[1] if len(args) > 1 else args[0]
            self._SET.append(Expr(Expr.Arg, key, value))
        for key, value in kwargs.items():
            self._SET.append(Expr(Expr.Kwarg, key, value))
        return self

    def ORDER(self, field, order=1):
        self._ORDER.append((field, order))
        return self

    def RETURNING(self, *args):
        self._RETURNING.extend(args)
        return self

    def ON_CONFLICT_DO_NOTHING(self):
        self._ON_CONFLICT_DO_NOTHING = True
        return self

    def END(self, debug_print=False):
        q = ""
        q_args = ()
        idx = 1

        q += self.main_cmd

        if self.main_cmd == self._M_SELECT:
            if self.select_fields not in (None, "*"):
                q += " " + ",".join(self._format_select_field(f) for f in self.select_fields)
            else:
                q += " *"

            q += " FROM " + quoted(self._FROM)
        elif self.main_cmd == self._M_INSERT:
            q += " INTO " + quoted(self._INSERT_TO)
        elif self.main_cmd == self._M_UPDATE:
            q += " " + quoted(self._UPDATE)
        elif self.main_cmd == self._M_DELETE:
            q += " " + quoted(self._DELETE)

        if self.main_cmd == self._M_INSERT:
            set_fields = []
            set_values = []
            set_args = ()
            for wh in self._SET:
                add_insert, add_value, add_args, idx = wh.format(idx)
                if not add_insert:
                    raise RuntimeError("Can't handle arg %s with INSERT" % wh)
                set_fields.append(add_insert)
                set_values.append(add_value)
                set_args += add_args

            q += " (" + ", ".join(set_fields) + ")"
            q += " VALUES (" + ", ".join(set_values) + ")"
            q_args += set_args

        if self.main_cmd == self._M_UPDATE:
            set_fields = []
            set_args = ()
            for wh in self._SET:
                add_insert, add_value, add_args, idx = wh.format(idx)
                set_fields.append("%s=%s" % (add_insert, add_value))
                set_args += add_args

            q += " SET " + ", ".join(set_fields)
            q_args += set_args

        if self._WHERE:
            q += " WHERE"
            where_fields = []
            where_args = ()
            for wh in self._WHERE:
                add_insert, add_value, add_args, idx = wh.format(idx)
                if add_insert:
                    where_fields.append("{add_insert}={add_value}".format(add_insert=add_insert, add_value=add_value))
                else:
                    where_fields.append("{add_value}".format(add_value=add_value))
                where_args += add_args
            q += " " + " AND ".join(where_fields)
            q_args += where_args

        if self._ORDER:
            order_fields = []
            for (field, order) in self._ORDER:
                order_fields.append(quoted(field) + (" DESC" if order == -1 else ""))
            q += " ORDER BY " + ", ".join(order_fields)

        if self._ON_CONFLICT_DO_NOTHING:
            q += " ON CONFLICT DO NOTHING"

        if self._RETURNING:
            q += " RETURNING " + ", ".join(quoted(f) if f != "*" else f for f in self._RETURNING)

        if debug_print:
            print('Q: %s; %s' % (q, q_args))

        return q, q_args

    @staticmethod
    def _format_select_field(field):
        if isinstance(field, Q.Unsafe):
            return field.value
        else:
            return quoted(field)


def test_q():
    assert Expr(Expr.Arg, "a", 5).format(1) == ('"a"', "$1", (5,), 2)
    assert Expr(Expr.Arg, None, 'a!=5').format(1) == (None, 'a!=5', (), 2)
    assert Expr(Expr.Arg, "a=ANY({})", [2, 4]).format(1) == (None, 'a=ANY($1)', ([2, 4],), 2)
    assert Expr(Expr.Arg, "a<={}", 3).format(1) == (None, 'a<=$1', (3,), 2)
    assert Expr(Expr.Arg, "a", Q.Any([1])).format(1) == ('"a"', "ANY($1)", ([1],), 2)
    assert Expr(Expr.Kwarg, "a", 5).format(1) == ('"a"', "$1", (5,), 2)
    assert Expr(Expr.Kwarg, "a", Q.Any([1])).format(1) == ('"a"', "ANY($1)", ([1],), 2)

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

    # Tests based on preserved order of kwargs are valid on Python 3.6+ only
    assert Q.INSERT("foo").SET(a=5, b=7).END() == ('INSERT INTO "foo" ("a", "b") VALUES ($1, $2)', (5, 7))

    assert Q.UPDATE("foo").SET(a=5, b=7).END() == ('UPDATE "foo" SET "a"=$1, "b"=$2', (5, 7))
    assert Q.UPDATE("foo").SET(a=5, b=7).WHERE(a=2).END() == ('UPDATE "foo" SET "a"=$1, "b"=$2 WHERE "a"=$3', (5, 7, 2))
    assert Q.UPDATE("foo").SET(a=Q.Unsafe("now()")).WHERE(a=2).END() == ('UPDATE "foo" SET "a"=now() WHERE "a"=$1', (2,))

    assert Q.DELETE("foo").END() == ('DELETE "foo"', ())
    assert Q.DELETE("foo").WHERE(a=2).END() == ('DELETE "foo" WHERE "a"=$1', (2,))


if __name__ == "__main__":
    test_q()
