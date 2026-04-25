import config
import logging
import os
from datetime import timedelta

from flask import Flask, send_from_directory
from flask_session import Session

from blueprints.admin import bp as admin_bp
from blueprints.auth import bp as auth_bp
from blueprints.boxes import bp as boxes_bp
from blueprints.pickem import bp as pickem_bp
from blueprints.survivor import bp as survivor_bp
from constants import UPLOAD_FOLDER


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

path = '/home/dheslin/dailybox'
dev_path = '/home/dheslin/bygtech/dailybox'

print(f"OS instance PATH {os.path.dirname(app.instance_path)}")
print(f"OS root PATH {os.path.dirname(app.root_path)}")
print(f"OS CWD {os.getcwd()}")
if config.env == 'prod' and os.getcwd() != path:
    os.chdir(path)
elif config.env == 'dev' and os.getcwd() != dev_path:
    os.chdir(dev_path)
print(f"OS CWD after: {os.getcwd()}")

logging.basicConfig(filename="byg.log", format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")
logging.info(f"OS instance PATH {os.path.dirname(app.instance_path)}")
logging.info(f"OS root PATH {os.path.dirname(app.root_path)}")
logging.info(f"OS CWD {os.getcwd()}")

if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.permanent_session_lifetime = timedelta(days=7)
Session(app)

app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(boxes_bp)
app.register_blueprint(pickem_bp)
app.register_blueprint(survivor_bp)

@app.route('/app', defaults={'path': ''})
@app.route('/app/<path:path>')
def spa(path):
    dist = os.path.join(app.root_path, 'static', 'dist')
    if path and os.path.exists(os.path.join(dist, path)):
        return send_from_directory(dist, path)
    return send_from_directory(dist, 'index.html')

if __name__ == "__main__":
    app.run(debug=True)
