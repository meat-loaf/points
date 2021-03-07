import flask
import json
from datetime import datetime
import sqlite3

import database

app = flask.Flask("points")
db_path = "./database.db"

def get_db_cxn():
	return sqlite3.connect(db_path)

@app.route("/points/<path:payer>/add", methods=['POST'])
def points_add(payer):
	dat = json.loads(flask.request.get_json())
	database.add_payer_points(get_db_cxn(), payer, dat['points'], dat['timestamp'])
	return app.response_class(status=201)

@app.route("/points/", defaults={'payer': None}, methods=['GET'])
@app.route("/points/<path:payer>", methods=['GET'])
def points_get(payer):
	dat = database.get_payer_points(get_db_cxn(), payer)
	return flask.jsonify(dat)

#ideally, this first route shouldn't exist, but mapping transactions to users wasn't done
@app.route("/points/spend/", defaults={'user': None}, methods=['POST'])
@app.route("/points/spend/<path:user>", methods=['POST'])
def points_spend(user):
	dat = json.loads(flask.request.get_json())
	ret = database.spend_payer_points(get_db_cxn(), user, dat['points'])
	if ret is None:
		return "Not enough points.", 400
	return flask.jsonify(ret)

def main():
	database.migrate(get_db_cxn())
	return app.run(host='0.0.0.0', port=9001)

if __name__ == '__main__':
	main()
