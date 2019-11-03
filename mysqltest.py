#!/usr/bin/env python3.6

import sys
import random
import json
import mysql.connector
from mysql.connector import errorcode


db_config = {'user':'root', 'password':'024!cH;cken', 'host':'localhost', 'database':'dailybox'}

def db(s, db_config=db_config):
    try:
        cnx = mysql.connector.connect(**db_config)
        print("try succeeded")

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

    cursor = cnx.cursor()
    print(s)
    cursor.execute(s)
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
'''
test python usage of mysql below
'''

# s = "SELECT * from boxnums where boxid = 5;"
s = "SELECT box_type from boxes where boxid = 1;"
test = db(s)
print(test)
print(type(test))
print(type(test[0][0]))




