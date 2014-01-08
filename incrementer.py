#!/usr/bin/env python

'''Increments a value 1000 times. Set up Postgres:

create database wtf;
\connect wtf;
create table test (id integer primary key not null, value integer not null, sum integer not null);
'''

import random
import sys

import psycopg2

def increment_row(connection, id):
    cursor = connection.cursor()

    update_failure_count = 0
    rollback_count = 0

    next_sum = None
    while True:
        try:
            # Single statement atomic increments:
            # cursor.execute('UPDATE test SET sum=sum+1 WHERE id=%s', (id,))
            # if cursor.rowcount == 1:
            #     # SUCCESS!
            #     break

            cursor.execute('SELECT value, sum FROM test WHERE id=%s', (id,))
            results = cursor.fetchone()
            value = results[0]
            current_sum = results[1]
            
            next_sum = current_sum + 1
            cursor.execute('UPDATE test SET sum=%s WHERE id=%s and value=%s and sum=%s', (next_sum, id, value, current_sum))
            if cursor.rowcount == 1:
                # SUCCESS!
                break

            update_failure_count += 1
        except psycopg2.extensions.TransactionRollbackError:
            # Assume: could not serialize access due to concurrent update
            rollback_count += 1
            connection.rollback()

    cursor.close()
    connection.commit()

    if update_failure_count > 0:
        print 'update failed %d time(s)' % (update_failure_count)
    if rollback_count > 0:
        print 'transaction rolled back %d time(s)' % (rollback_count)
    return next_sum


def example():
    connection = psycopg2.connect('dbname=wtf')

    # Change isolation
    cursor = connection.cursor()
    # Default = READ COMMITTED same as READ UNCOMMITTED
    cursor.execute('SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ UNCOMMITTED');
    # cursor.execute('SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL REPEATABLE READ');
    # cursor.execute('SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL SERIALIZABLE');
    cursor.close()
    connection.commit()

    # Turn on "autocommit" (default = False)
    # connection.autocommit = True

    for i in xrange(1000):
        value = increment_row(connection, 1)
        # print 'incremented to', value

    print 'last value:', value
    connection.close()


if __name__ == '__main__':
    example()
