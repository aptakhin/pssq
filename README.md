Prepares PostgreSQL queries for execution in more useful Pythonic way. Not ORM.

    >>> from pssq import Q
    >>> Q.SELECT().FROM("foo").WHERE(a=5).END()
    ('SELECT * FROM "foo" WHERE "a"=$1', (5,))

    >>> Q.INSERT("foo").SET(a=5, b=7).END()
    ('INSERT INTO "foo" ("a", "b") VALUES ($1, $2)', (5, 7))
    
    >>> Q.INSERT("foo").SET(q=Q.Unsafe("4"), w=Q.Unsafe("now()"), a=5).END()
    ('INSERT INTO "foo" ("q", "w", "a") VALUES (4, now(), $1)', (5,))


## Install
    
    pip3 install pssq
    
    
## Tests

    pip3 install pytest
    PYTHONPATH=src py.test -s tests
    
    
