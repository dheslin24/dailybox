#!/usr/bin/env python3
import psutil
import subprocess
import signal
import os
import time

flask_apps = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'flask' in p.info['name']]

print(flask_apps)

for f in flask_apps:
    pid = f['pid'] 
    print("killing pid {}".format(pid))
    os.kill(int(pid), signal.SIGTERM)
    # Check if the process that we killed is alive.
    '''
    try: 
       os.kill(int(pid), 0)
       raise Exception("""wasn't able to kill the process 
                          HINT:use signal.SIGKILL or signal.SIGABORT""")
    except OSError as ex:
       continue
    '''

print("starting flask")
#subprocess.run(['flask', 'run', '-h', '0.0.0.0', '-p', '10001', '%'], shell=True)
subprocess.run(["flask run -h 0.0.0.0 -p 10001 &"], shell=True, cwd="/home/dheslin/dailybox")

time.sleep(5)

new_flask_app = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'flask' in p.info['name']]
print("new flask app running with pid {}".format(new_flask_app))


