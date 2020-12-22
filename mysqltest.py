#!/usr/bin/env python3.6

import sys
import random
import json
import mysql.connector
from mysql.connector import errorcode
import config


# imported config
db_config = {'user':config.user, 'password':config.password, 'host':config.host, 'database':config.database}


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
# s = "SELECT x, y from boxnums where boxid = 39;"
# s = "SELECT ended FROM es_end_game where boxid = 31;"
# s = "SELECT score_num, winning_box FROM everyscore where boxid = 31;"
# s = "SELECT username FROM users WHERE userid = 11;"
# s = "SELECT boxid from boxes where pay_type = 3 and active = 1;"
# s = "SELECT box_type, pay_type from boxes where boxid = 35;"
# s = "SELECT userid, username from users;"
# s = "SELECT boxid, score_num from everyscore order by boxid, score_num;"
# s = "SELECT x_score FROM everyscore ORDER BY score_id DESC limit 1;"
# s = "SELECT score_num, x_score, y_score FROM everyscore ORDER BY score_id DESC limit 1;"
# s = "SELECT box_type, pay_type FROM boxes WHERE boxid = 41;"
# s = "SELECT box1, box2, box3 from boxes where boxid = 44;"
# s = "SELECT boxid, winner FROM scores ORDER BY score_id ASC;"
# s = "SELECT b.boxid from boxes b left join scores s on b.boxid = s.boxid where s.winner is NULL and b.active = 0;"
# s = "SELECT username FROM users WHERE userid = 11;"
s = "SELECT max_boxes from max_boxes where userid = 10;"


test = db(s)
print("test")
print(test)
print(type(test))
#print(type(test[0][0]))
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

