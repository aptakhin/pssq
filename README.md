Builds PostgreSQL queries for execution in more useful Pythonic way. Not ORM.

    >>> from pssq import Q
    >>> Q.select().from_("foo").where(a=5).end()
    ('SELECT * from "foo" where "a"=$1', (5,))

    >>> Q.insert("foo").set(a=5, b=7).end()
    ('INSERT INTO "foo" ("a", "b") VALUES ($1, $2)', (5, 7))
    
    >>> Q.insert("foo").set(q=Q.unsafe("4"), w=Q.unsafe("now()"), a=5).end()
    ('INSERT INTO "foo" ("q", "w", "a") VALUES (4, now(), $1)', (5,))


## Install
    
    pip3 install pssq
    
    
## Tests

    pip3 install pytest
    PYTHONPATH=src py.test -s tests
    
    
