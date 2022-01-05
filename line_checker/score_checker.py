#!/usr/bin/python3

from db_accessor import db2 
import logging
#import random
import time
import sys
from espnapi import get_espn_score_by_qtr

logging.basicConfig(filename="score_checker.log", format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")
starttime = time.mktime((2021, 12, 17, 18, 59, 0, 0, 0, 0))

print(sys.argv)
if len(sys.argv) < 1:
    print("Usage:  ./score_checker.py <boxid> <espnid>")
    
else:
    boxid = sys.argv[1]
    if len(sys.argv) < 2: # missing espnid, go look it up
        s = "SELECT espn_id FROM boxes WHERE boxid = %s;"
        espnid = db2(s, (boxid,))
        print(f"espnid from db: {espnid}")
    else:
        espnid = sys.argv[2]

    scores = get_espn_score_by_qtr(espnid)

    print(scores)
    
    # {'LSU': {'schoolName': 'LSU', 'nickname': 'Tigers', 'logo': 
    # 'https://a.espncdn.com/i/teamlogos/ncaa/500/99.png', 'current_score': '0', 
    # 'qtr_scores': {1: 0, 2: 0, 3: 0, 4: 0}}, 
    # 'KSU': {'schoolName': 'Kansas State', 'nickname': 'Wildcats', 'logo': 
    # 'https://a.espncdn.com/i/teamlogos/ncaa/500/2306.png', 'current_score': '0', 
    # 'qtr_scores': {1: 0, 2: 0, 3: 0, 4: 0}}}

    x1 = scores['KSU']['qtr_scores'][1]
    x2 = scores['KSU']['qtr_scores'][2] + x1
    x3 = scores['KSU']['qtr_scores'][3] + x2
    x4 = scores['KSU']['qtr_scores'][4] + x3
    y1 = scores['LSU']['qtr_scores'][1]
    y2 = scores['LSU']['qtr_scores'][2] + y1
    y3 = scores['LSU']['qtr_scores'][3] + y2
    y4 = scores['LSU']['qtr_scores'][4] + y3

    q = "INSERT INTO scores (boxid, x1, y1, x2, y2, x3, y3, x4, y4) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"
    db2(q, (boxid, x1, y1, x2, y2, x3, y3, x4, y4))

    #time.sleep(300.0 - ((time.time() - starttime) % 300.0))