import config
import logging
import mysql.connector
from mysql.connector import errorcode
from mysql.connector.pooling import MySQLConnectionPool

db_config = {'user': config.user, 'password': config.password, 'host': config.host, 'database': config.database}

_pool = MySQLConnectionPool(pool_name="main", pool_size=10, **db_config)


def db2(s, params=(), **kwargs):
    try:
        cnx = _pool.get_connection()
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logging.error("DB connection: invalid credentials")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            logging.error("DB connection: database does not exist")
        else:
            logging.error("DB connection failed: %s", err)
        raise

    try:
        cursor = cnx.cursor()
        if params:
            logging.debug("db2: %s | params: %s", s[:120], params)
            cursor.execute(s, params)
        else:
            logging.debug("db2: %s", s[:120])
            cursor.execute(s)

        if s.lstrip()[:4].upper() in ("SELE", "SHOW", "DESC"):
            rv = cursor.fetchall()
            cursor.close()
            return rv
        else:
            cnx.commit()
            cursor.close()
            return ()
    finally:
        cnx.close()  # returns connection to pool, does not teardown
