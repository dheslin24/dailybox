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
# s = "SELECT username from users where userid = 11;"
# s = "SELECT * from scores where boxid = 13 order by score_id desc limit 1;"
# s = "SELECT pay_type from boxes where boxid = 11;"
# s = "SELECT boxid, winner from scores order by score_id desc;"
# s = "SELECT boxid from boxes where gobbler_id = 1;"
# s = "SELECT b.boxid, b.box_name, b.fee, pt.description, s.winner FROM boxes b LEFT JOIN pay_type pt ON b.pay_type = pt.pay_type_id LEFT JOIN scores s ON s.boxid = b.boxid WHERE b.active = 0 and b.box_type = 3 limit 1;"
# s = "SELECT home, away FROM teams WHERE boxid = 21;"
# s = "SELECT x, y from boxnums where boxid = 24;"
# s = "SELECT ended FROM es_end_game where boxid = 31;"
# s = "SELECT score_num, winning_box FROM everyscore where boxid = 31;"
# s = "SELECT username FROM users WHERE userid = 11;"
# s = "SELECT boxid from boxes where pay_type = 3 and active = 1;"
s = "SELECT box_type, pay_type from boxes where boxid = 35;"
test = db(s)
print("test")
print(test)
print(type(test))
print(type(test[0][0]))
print("test[0]")
if len(test) > 0:
    print(test[0])
    print("len(test[0])")
    print(len(test[0]))
else:
    print(len(test))
'''
print("test[0][0]")
print(test[0][0])
print(test[0][1])
x = json.loads(test[0][0])
y = json.loads(test[0][1])
print(x['4'])
print(y['9'])

'''


