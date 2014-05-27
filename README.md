# Can you do an atomic test-and-set using Postgres?

[Adam Marcus](http://marcua.net/) [asked this question](https://twitter.com/marcua/status/420995314838167553). I had something similar lying around and I was curious about the answer so I cooked up this test. There is a detailed description of why this works at the end.


## Generic test-and-set

Basically, do a `SELECT` followed by an `UPDATE WHERE value=x AND value2=y AND ...` to check that values you care about haven't changed. You then need to wrap this in a retry loop. There are two "failure" cases:

1. `UPDATE` fails to match any rows (`cursor.rowcount == 0` in Python). This happens for all isolation levels, but is the only failure case for `READ COMMITTED`.
2. Postgres rolls back your transaction (`TransactionRollbackError` in Python). This happens for `REPEATABLE READ` and `SERIALIZABLE`, even in autocommit mode (since autocommit is the same as explicitly executing `BEGIN` and `COMMIT`).


### Random notes

* Postgres's [default and weakest isolation](http://www.postgresql.org/docs/9.3/static/sql-set-transaction.html) is `READ COMMITTED`.
* Postgres doesn't support `READ UNCOMMITTED`, so it gets treated as `READ COMMITTED`.
* Postgres's [MVCC documentation](http://www.postgresql.org/docs/9.3/static/mvcc.html) specifies the details.


## Atomic increment

Executing an increment (or any other expression evaluated by Postgres) in a single `UPDATE` statement is also atomic. Again, you need to check that some row was in fact updated, or if a rollback occurred.


## Running this yourself

This test program runs 1000 increments. You can run multiple concurrent instances and verify that the final count is a multiple of 1000. If it isn't, some increments were lost and it wasn't atomic.

1. Setup Postgres:

   ```sql
create database wtf;
\connect wtf;
create table test (id integer primary key not null, value integer not null, sum integer not null);
insert into test values (1, 0, 0);
```

2. Run `./incrementer.py` in multiple consoles concurrently.
3. Edit the program to switch isolation modes, or between the single statement and multi-statement versions.


### Why does this work for `READ COMMITTED`?

The [Postgres Transaction Isolation documentation](http://www.postgresql.org/docs/9.3/static/transaction-iso.html) does a good job describing the internals. The summary is that a single row update acquires a database-wide write lock and performs the update only if the `WHERE` expression is true, so this is atomic in all isolation levels.

For a single statement at the weakest (and default) `READ COMMITTED` isolation level, Postgres first obtains a new snapshot and searches for rows matching the condition. For each row it finds, it obtains a write lock. After it obtains the write lock, *it re-evaluates the condition on the most recent version of this row*. If it still matches, the update is applied. Postgres holds write locks until the transaction commits or aborts.

For this example, the read step may not find a matching row if it has already been modified. In this case, it returns zero modified rows. If it finds a row, the transaction acquires a write lock. After acquiring the lock, the `WHERE` clause is re-evaluated. If it no longer matches, the transaction returns zero modified rows. If it matches, then it means the row has not been updated, the write proceeds, and the statement returns 1 modified row. Because the `WHERE` clause is checked while holding the write lock, this is atomic.


### Why does this work for `REPEATABLE READ`?

The stronger `REPEATABLE READ` level implements snapshot isolation, which has two important differences:

* The snapshot is acquired when the transaction begins, and is held until the transaction commits (instead of acquired when the statement begins and released when it commits).
* If a row has been updated when a transaction obtains a write lock, the transaction aborts with a serializability error (instead of attempting to apply the update to the updated row).

For this example, neither of these differences matter, except that it causes a serializability error to be returned instead of modifying zero rows. The effect is still the same: when the write lock is granted, the row has not been updated, so this is atomic.
