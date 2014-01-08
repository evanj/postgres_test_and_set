# Can you do an atomic test-and-set using Postgres?

[Adam Marcus](http://marcua.net/) [asked this question](https://twitter.com/marcua/status/420995314838167553). I had something similar lying around and I was curious about the answer so I cooked up this test.


## Generic test-and-set

Basically, do a `SELECT` followed by an `UPDATE WHERE value=x AND value2=y AND ...` to check that values you care about haven't changed. You then need to wrap this in a retry loop. There are two "failure" cases:

1. `UPDATE` fails to match any rows (`cursor.rowcount == 0` in Python). This happens for `READ COMMITTED`.
2. Postgres rolls back your entire transaction (`TransactionRollbackError` in Python). This happens for `REPEATABLE READ` or `SERIALIZABLE` (even in autocommit mode, which surprises me, maybe I'm doing something wrong?).


### Random notes

* Postgres's default isolation is `READ COMMITTED`.
* Postgres doesn't support `READ UNCOMMITTED`, so it gets treated as `READ COMMITTED`.


## Atomic increment

It appears that executing an increment in a single `UPDATE` statement is atomic. Again, you need to check that some row was in fact updated, or if a rollback occurred.



## Running this yourself

This test program runs 1000 increments. You can run multiple concurrent instances and verify that the final count is a multiple of 1000. If it isn't, some increments were lost and it wasn't atomic.

1. Setup Postgres:

   ```sql
create database wtf;
\connect wtf;
create table test (id integer primary key not null, value integer not null, sum integer not null);
```

2. Run `./incrementer.py` in multiple consoles concurrently.
