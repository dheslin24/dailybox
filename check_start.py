#!/usr/bin/env python3
import psutil
import subprocess
# import signal
# import os
import time


flask_apps = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'flask' in p.info['name']]

print(flask_apps)

if not flask_apps:
    print("starting flask")
    #subprocess.run(['flask', 'run', '-h', '0.0.0.0', '-p', '10001', '%'], shell=True)
    subprocess.run(["flask run -h 0.0.0.0 -p 10001 &"], shell=True)

    time.sleep(5)

    new_flask_app = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'flask' in p.info['name']]
    print("new flask app running with pid {}".format(new_flask_app))




