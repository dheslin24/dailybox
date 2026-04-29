import config
import logging
import mysql.connector
from mysql.connector import errorcode

db_config = {'user': config.user, 'password': config.password, 'host': config.host, 'database': config.database}


def db2(s, params=(), db_config=db_config):
    try:
        cnx = mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logging.error("DB connection: invalid credentials")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            logging.error("DB connection: database does not exist")
        else:
            logging.error("DB connection failed: %s", err)
        raise

    cursor = cnx.cursor()
    if params:
        logging.debug("db2: %s | params: %s", s[:120], params)
        cursor.execute(s, params)
    else:
        logging.debug("db2: %s", s[:120])
        cursor.execute(s)

    rv = ()
    if s.lstrip()[:4].upper() in ("SELE", "SHOW", "DESC"):
        rv = cursor.fetchall()
        cursor.close()
        cnx.close()
        return rv
    else:
        cnx.commit()
        cursor.close()
        cnx.close()
