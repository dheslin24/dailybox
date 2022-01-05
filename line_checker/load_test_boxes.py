#!/usr/bin/python3

from db_accessor import db2 
import logging
import random
import sys

logging.basicConfig(filename="load_boxes.log", format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")

print(sys.argv)
if len(sys.argv) < 1:
    print("Usage:  ./load_test_boxes <boxid>")
    
else:
    boxid = sys.argv[1]

    # | boxid      | int          | NO   | PRI | NULL    | auto_increment |
    # | active     | tinyint      | YES  |     | NULL    |                |
    # | box_type   | int          | YES  |     | NULL    |                |
    # | box_name   | varchar(255) | YES  |     | NULL    |                |
    # | fee        | int          | YES  |     | NULL    |                |
    # | pay_type   | int          | YES  |     | NULL    |                |
    # | gobbler_id | int          | YES  |     | NULL    |                |
    # | espn_id

    users = [3, 4, 5, 6, 7, 8] # all test users in both dev/prod

    bs = ''
    for i in range(100):
        bs += 'box' + str(i) + ' = ' + str(random.choice(users)) + ', '
    bs = bs[:-2]

    query = f"UPDATE boxes SET {bs} WHERE boxid = {boxid};"

    print(query)

    db2(query)
    