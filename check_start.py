#!/usr/bin/env python3
import psutil
import subprocess
import time
import logging

logging.basicConfig(filename="check_start.log", format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")


flask_apps = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'flask' in p.info['name']]
line_checker_app = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'line_checker' in p.info['name']]

week = 1
season = 3 # 1 pre, 2 reg, 3 post
league = "nfl"

if not flask_apps:
    print("starting flask")
    logging.info("starting flask")
    subprocess.run(["flask run -h 0.0.0.0 -p 10001 &"], shell=True, cwd="/home/dheslin/dailybox")

    time.sleep(5)

    new_flask_app = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'flask' in p.info['name']]
    print(f"new flask app running with pid {new_flask_app}")
    logging.info(f"new flask app running with pid {new_flask_app}")


if not line_checker_app:
    print("starting line_checker")
    logging.info("starting line_checker")

    subprocess.run([f"python ./line_checker/line_checker.py {season} {week} {league}&"], shell=True, cwd="/home/dheslin/dailybox")

    time.sleep(5)

    new_line_checker = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'line_checker' in p.info['name']]
    print(f"new line checker running with pid {new_line_checker}")
    logging.info(f"new line checker running with pid {new_line_checker}")


