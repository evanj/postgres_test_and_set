= Can you do an atomic test-and-set using Postgres?

Adam Marcus asked this question (in a tweet)[https://twitter.com/marcua/status/420995314838167553]. I had something similar lying around, so I cooked up this test.


== Making generic test-and-set work

Basically, do a `SELECT` followed by an `UPDATE` with a `WHERE` that checks the values you care about. You then need to wrap this in a retry loop. There are two "failure" cases:

1. `UPDATE` fails to match any rows (`cursor.rowcount == 0` in Python). This happens for READ COMMITTED.
2. Postgres rolls back the transaction (`TransactionRollbackError` in Python). This happens for REPEATABLE READ or SERIALIZABLE.


== Atomic increment

It appears that executing an increment in a single `UPDATE` statement is atomic. Again, you need to check that some row was in fact updated, or if a rollback occurred.


== Running this yourself

This test program runs 1000 increments. You can run multiple instances, and then final count should be a multiple of 1000. If it isn't, you know some increments were lost.

=== Setup Postgres

```sql
create database wtf;
\connect wtf;
create table test (id integer primary key not null, value integer not null, sum integer not null);
```

== Run it

You'll need the `psycopg2` module, but then run: `./incrementer.py` in multiple consoles concurrently.
