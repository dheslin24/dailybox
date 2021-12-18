# mysql stuff
import mysql.connector
from mysql.connector import errorcode

# imported config
import config 
db_config = {'user':config.user, 'password':config.password, 'host':config.host, 'database':config.database}
# print(db_config)

def db2(s, params=(), db_config=db_config):
    try:
        cnx = mysql.connector.connect(**db_config)
        #print("try succeeded")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Invalid Username or Password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    #else:
        #print("try failed")
        #cnx.close()

    if len(params) == 0:
        cursor = cnx.cursor()
        print(s)
        cursor.execute(s)
    else:
        cursor = cnx.cursor()
        print("db2 executing")
        print(s, params)
        cursor.execute(s, params)

    rv = ()
    if s[:6] == "SELECT":
        rv = cursor.fetchall()
        cursor.close()
        cnx.close()
        return rv
    else:
        cnx.commit()
        cursor.close()
        cnx.close()