#!/usr/bin/python3

from db_accessor.db_accessor import db2 
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

    while True:

        scores = get_espn_score_by_qtr(espnid)

        print(scores)
        
        # {'LSU': {'schoolName': 'LSU', 'nickname': 'Tigers', 'logo': 
        # 'https://a.espncdn.com/i/teamlogos/ncaa/500/99.png', 'current_score': '0', 
        # 'qtr_scores': {1: 0, 2: 0, 3: 0, 4: 0}}, 
        # 'KSU': {'schoolName': 'Kansas State', 'nickname': 'Wildcats', 'logo': 
        # 'https://a.espncdn.com/i/teamlogos/ncaa/500/2306.png', 'current_score': '0', 
        # 'qtr_scores': {1: 0, 2: 0, 3: 0, 4: 0}}}

        qtrs = []
        print(f"scores {scores}")
        # for team in scores:
        #     q = len(scores[team]['qtr_scores'])
        #     print(f"q:  --  {q}")
        #     if q > 0:
        #         for qtr in scores[team]['qtr_scores']:
        #             print(f"qtr -- {qtr}")
        #             if qtr <= q or qtr == 4:
        #                 qtrs.append(scores[team]['qtr_scores'][qtr])

        # ALA then UGA
        q = len(scores['ALA']['qtr_scores'])
        print(f"q:  --  {q}")
        if q > 0:
            for qtr in scores['ALA']['qtr_scores']:
                print(f"qtr -- {qtr}")
                if qtr <= q or qtr == 4:
                    qtrs.append(scores['ALA']['qtr_scores'][qtr])
            for qtr in scores['UGA']['qtr_scores']:
                print(f"qtr -- {qtr}")
                if qtr <= q or qtr == 4:
                    qtrs.append(scores['UGA']['qtr_scores'][qtr])
            

        print(f"qtrs:  --- {qtrs}")           
        quarter = len(qtrs) // 2
        cols = ''
        vals = ''
        total_x = 0
        total_y = 0
        if qtrs:
            yq = 1
            for y_qtr in qtrs[:quarter]:
                print(f"yqtr {y_qtr}")
                cols += 'y' + str(yq) + ', '
                vals += str(total_y + int(y_qtr)) + ', '
                total_y += int(y_qtr)
                yq += 1
            xq = 1
            for x_qtr in qtrs[quarter:]:
                print(f"xqtr {x_qtr}")
                cols += 'x' + str(xq) + ', '
                vals += str(total_x + int(x_qtr)) + ', '
                total_x += int(x_qtr)
                xq += 1
        if len(cols) > 1:
            cols = cols[:-2]
            vals = vals[:-2]   

            q = f"INSERT INTO scores (boxid, {cols}) VALUES ({boxid}, {vals});"
            db2(q)
            print(q)
            #break


        time.sleep(60.0 - ((time.time() - starttime) % 60.0))