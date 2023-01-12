#!/usr/bin/env python3
import psutil
import subprocess
# import signal
# import os
import time
import logging

logging.basicConfig(filename="check_start.log", format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")


flask_apps = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'flask' in p.info['name']]

print(flask_apps)
logging.info(flask_apps)

if not flask_apps:
    print("starting flask")
    logging.info("starting flask")
    #subprocess.run(['flask', 'run', '-h', '0.0.0.0', '-p', '10001', '%'], shell=True)
    subprocess.run(["flask run -h 0.0.0.0 -p 10001 &"], shell=True, cwd="/home/dheslin/dailybox")

    time.sleep(5)

    new_flask_app = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'flask' in p.info['name']]
    print("new flask app running with pid {}".format(new_flask_app))
    logging.info("new flask app running with pid {}".format(new_flask_app))




