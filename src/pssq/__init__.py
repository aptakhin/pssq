
def quoted(s):
    return '"%s"' % s


class _Unsafe:
    __slots__ = ['value']

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return 'Q.Unsafe(%s)' % repr(self.value)


class _Any:
    __slots__ = ['value']

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return 'Q.Any(%s)' % repr(self.value)


class Expr:
    Arg = 'arg'
    Kwarg = 'kwarg'

    def __init__(self, tp, key, value=None):
        self.tp = tp
        self.key = key
        self.value = value

    def format(self, idx):
        if self.tp == self.Arg:
            if self.key and '{}' in self.key:
                insert = None
                key = self.key.replace('{}', '$%d' % idx)
                value = (self.value,) if self.key is not None else ()
                idx += 1
            elif isinstance(self.value, _Any):
                insert = quoted(self.key)
                key = 'ANY($%d)' % idx
                value = (self.value.value,)
                idx += 1
            else:
                insert = quoted(self.key) if self.key is not None else None
                key = '$%d' % idx if self.key is not None else self.value
                value = (self.value,) if self.key is not None else ()
                idx += 1

            res = insert, key, value, idx
        elif self.tp == self.Kwarg:
            insert = quoted(self.key) if self.key is not None else None
            if isinstance(self.value, _Unsafe):
                key = str(self.value)
                value = ()
            elif isinstance(self.value, _Any):
                key = 'ANY($%d)' % idx
                value = (self.value.value,)
                idx += 1
            else:
                key = '$%d' % idx if self.key is not None else self.value
                value = (self.value,) if self.key is not None else ()
                idx += 1

            res = insert, key, value, idx
        else:
            raise ValueError('Unhandled type %s' % repr(self.tp))

        return res

    def __repr__(self):
        return 'Expr(%s, %s, %s)' % (repr(self.tp),
                                     repr(self.key),
                                     repr(self.value))


class Q:
    _M_SELECT = 'SELECT'
    _M_INSERT = 'INSERT'
    _M_UPDATE = 'UPDATE'
    _M_DELETE = 'DELETE'

    @staticmethod
    def select(fields=None):
        q = Q(main_cmd=Q._M_SELECT)
        if fields is None:
            fields = '*'
        elif isinstance(fields, str):
            fields = [f.strip() for f in fields.split(',')]

        if fields != '*' and not isinstance(fields, list):
            fields = [fields]

        q.select_fields = fields
        return q

    @staticmethod
    def insert(table):
        q = Q(main_cmd=Q._M_INSERT)
        q._insert_to = table
        return q

    @staticmethod
    def update(table):
        q = Q(main_cmd=Q._M_UPDATE)
        q._update = table
        return q

    @staticmethod
    def delete():
        q = Q(main_cmd=Q._M_DELETE)
        return q

    @staticmethod
    def any(value):
        return _Any(value)

    @staticmethod
    def unsafe(value):
        return _Unsafe(value)

    def __init__(self, main_cmd=None):
        self.main_cmd = main_cmd
        assert main_cmd in (None, Q._M_SELECT, Q._M_INSERT,
                            Q._M_UPDATE, Q._M_DELETE)
        self.select_fields = None
        self.update_fields = None

        self._from = None
        self._insert_to = None
        self._update = None
        self._delete = None

        self._where = []
        self._set = []
        self._order = []
        self._returning = []
        self._on_conflict_do_nothing = None

    def from_(self, table):
        self._from = table
        return self

    def where(self, *args, **kwargs):
        if args and kwargs:
            raise RuntimeError("Can't understand args and kwargs in where")
        if args:
            key = args[0] if len(args) > 1 else None
            value = args[1] if len(args) > 1 else args[0]
            self._where.append(Expr(Expr.Arg, key, value))
        for key, value in kwargs.items():
            self._where.append(Expr(Expr.Kwarg, key, value))
        return self

    def set_(self, *args, **kwargs):
        if args:
            key = args[0] if len(args) > 1 else None
            value = args[1] if len(args) > 1 else args[0]
            self._set.append(Expr(Expr.Arg, key, value))
        for key, value in kwargs.items():
            self._set.append(Expr(Expr.Kwarg, key, value))
        return self

    def order(self, field, order=1):
        self._order.append((field, order))
        return self

    def returning(self, *args):
        self._returning.extend(args)
        return self

    def on_conflict_do_nothing(self):
        self._on_conflict_do_nothing = True
        return self

    def end(self, debug_print=False):
        q = ''
        q_args = ()
        idx = 1

        q += self.main_cmd

        if self.main_cmd == self._M_SELECT:
            if self.select_fields not in (None, '*'):
                q += ' ' + ','.join(self._format_select_field(f)
                                    for f in self.select_fields)
            else:
                q += ' *'

            q += ' FROM ' + quoted(self._from)
        elif self.main_cmd == self._M_DELETE:
            q += ' FROM ' + quoted(self._from)
        elif self.main_cmd == self._M_INSERT:
            q += ' INTO ' + quoted(self._insert_to)
        elif self.main_cmd == self._M_UPDATE:
            q += ' ' + quoted(self._update)
        elif self.main_cmd == self._M_DELETE:
            q += ' ' + quoted(self._delete)

        if self.main_cmd == self._M_INSERT:
            set_fields = []
            set_values = []
            set_args = ()
            for wh in self._set:
                add_insert, add_value, add_args, idx = wh.format(idx)
                if not add_insert:
                    raise RuntimeError("Can't handle arg %s with INSERT" % wh)
                set_fields.append(add_insert)
                set_values.append(add_value)
                set_args += add_args

            q += ' (' + ', '.join(set_fields) + ')'
            q += ' VALUES (' + ', '.join(set_values) + ')'
            q_args += set_args

        if self.main_cmd == self._M_UPDATE:
            set_fields = []
            set_args = ()
            for wh in self._set:
                add_insert, add_value, add_args, idx = wh.format(idx)
                set_fields.append('%s=%s' % (add_insert, add_value))
                set_args += add_args

            q += ' SET ' + ', '.join(set_fields)
            q_args += set_args

        if self._where:
            q += ' WHERE'
            where_fields = []
            where_args = ()
            for wh in self._where:
                add_insert, add_value, add_args, idx = wh.format(idx)
                if add_insert:
                    where_fields.append('{add_insert}={add_value}'
                                        .format(add_insert=add_insert,
                                                add_value=add_value))
                else:
                    where_fields.append('{add_value}'
                                        .format(add_value=add_value))
                where_args += add_args
            q += ' ' + ' AND '.join(where_fields)
            q_args += where_args

        if self._order:
            order_fields = []
            for (field, order) in self._order:
                order_fields.append(quoted(field) +
                                    (' DESC' if order == -1 else ''))
            q += ' ORDER BY ' + ', '.join(order_fields)

        if self._on_conflict_do_nothing:
            q += ' ON CONFLICT DO NOTHING'

        if self._returning:
            q += ' RETURNING ' + ', '.join(
                quoted(f) if f != '*' else f for f in self._returning)

        if debug_print:
            print('Q: %s; %s' % (q, q_args))

        return q, q_args

    @staticmethod
    def _format_select_field(field):
        if isinstance(field, _Unsafe):
            return field.value
        else:
            return quoted(field)
