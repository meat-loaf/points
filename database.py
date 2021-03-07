from itertools import chain

def _make_payer_points(payer, points):
	return {"payer": payer, "points": points}

def migrate(db):
	cursor = db.cursor();
	cursor.execute("PRAGMA foreign_keys = ON;")
	cursor.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, user_name TEXT)")
	cursor.execute("CREATE TABLE IF NOT EXISTS payers(payer_id INTEGER PRIMARY KEY, payer_name TEXT)")
	cursor.execute("""CREATE TABLE IF NOT EXISTS user_transactions(transaction_id INTEGER PRIMARY KEY, user_id INT,
		timestamp TEXT, posted_timestamp TEXT,
		FOREIGN KEY(user_id) REFERENCES users(user_id))""")
	cursor.execute("""CREATE TABLE IF NOT EXISTS payer_transactions(transaction_id INTEGER PRIMARY KEY, payer_id INT,
		points INT, timestamp TEXT, posted_timestamp TEXT,
		FOREIGN KEY(payer_id) REFERENCES payers(payer_id))""")
	cursor.execute("""INSERT INTO users(user_name) VALUES ('admin') EXCEPT SELECT user_name
			  FROM users WHERE user_name = 'admin'""")
	db.commit()

def add_payer_points(db, payer, points, timestamp):
	if db is None:
		raise Exception("Need database connection.")
	elif payer is None or points is None or timestamp is None:
		raise Exception("Invalid data.")
	cursor = db.cursor()
	cursor.execute("""INSERT INTO payers(payer_name) VALUES(?)
			EXCEPT SELECT payer_name FROM payers where payer_name = ?"""
			, (payer, payer))
	cursor.execute("SELECT payer_id from payers where payer_name = ?", (payer,))
	payer_id = cursor.fetchall()[0][0]
	cursor.execute("""INSERT INTO payer_transactions(payer_id, points, timestamp, posted_timestamp)
			VALUES (?, ?, ?, datetime('now', 'utc'))""", (payer_id, points, timestamp))
	db.commit()

def get_payer_points(db, payer=None):
	if db is None:
		raise Exception("Need database connection.")
	ret = None
	cursor = db.cursor()
	if payer is None:
		cursor.execute("""SELECT payers.payer_name, sum(points) FROM payer_transactions
				  JOIN payers ON payers.payer_id = payer_transactions.payer_id
				  GROUP BY payer_name""")
		ret = list()
		for item in cursor.fetchall():
			ret.append(_make_payer_points(item[0], item[1]))
	else:
		cursor.execute("""SELECT payer_name, sum(points) FROM payer_transactions
				  JOIN payers ON payers.payer_id = payer_transactions.payer_id
			          WHERE payer_name = ? GROUP BY payer_name""", (payer,))
		dat = cursor.fetchall()
		ret = _make_payer_points(dat[0][0], dat[0][1])
	return ret
	

def spend_payer_points(db, user, points):
	if db is None:
		raise Exception("Need database connection.")
	cursor = db.cursor()
	# short circuit if there's not enough total points to spend
	cursor.execute("SELECT sum(points) from payer_transactions")
	if cursor.fetchall()[0][0] < points:
		# not enough points
		return None

	# build an ordered list of transactions, removing points from the oldest transaction as they are spent
	# the result is a list of spendable points, oldest first
	payer_points = list()
	cursor.execute("""SELECT payer_name, points, posted_timestamp, payers.payer_id FROM payer_transactions
			  JOIN payers ON payers.payer_id = payer_transactions.payer_id
			  ORDER BY timestamp ASC""")
	for item in cursor.fetchall():
		if item[1] > 0:
			payer_points.append((item[0], item[1], item[2], item[3]))
		else:
			payer_ix = None
			remove = None
			# find list index for payer
			for i in range(0,len(payer_points)):
				if payer_points[i][3] == item[3]:
					payer_ix = i
			if payer_ix is None:
				payer_points.append((item[0], item[1], item[2], item[3]))
				payer_ix = len(payer_points)-1
			# update payer's points for this transaction row. if points are zero, remove the row
			if item[1] < 0 and payer_points[payer_ix][1]-item[1] == 0:
				remove = payer_ix
				break
			else:
				remove = None
				payer_points[payer_ix] = (
					payer_points[payer_ix][0], payer_points[payer_ix][1]+item[1], payer_points[payer_ix][2], payer_points[payer_ix][3])
			if remove is not None:
				payer_points.pop(remove)
	update = dict()
	points_spend = 0
	# build a dictionary of tuples:
	# * key is the payer_id
	# * value is a tuple: (points_spent, payer_name)
	# * points spent is negative
	for item in payer_points:
		if item[1] < (points - points_spend):
			points_spend += item[1]
			if item[3] not in update:
				update[item[3]] = (0-item[1], item[0])
			else:
				update[item[3]] = ((update[item[3]][0] - item[1]), item[0])
		else:
			spent = points - points_spend
			points_spend += spent
			if item[3] not in update:
				update[item[3]] = (0-spent, item[0])
			else:
				update[item[3]] = ((update[item[3]][0] - spent), item[0])
		if points_spend == points:
			break

	ret = list()
	dbupd = list()
	for key in update:
		ret.append(_make_payer_points(update[key][1], update[key][0]))
		dbupd.append((key, update[key][0]))
#	found here: https://stackoverflow.com/questions/22639343/sql-insert-with-multiple-rows-of-values-using-jython-and-zxjdbc
	stmt = "INSERT INTO payer_transactions (payer_id, points, timestamp, posted_timestamp) VALUES {}".format(
		','.join("(?, ?, datetime('now', 'utc'), datetime('now', 'utc'))" for _ in dbupd))
	cursor.execute(stmt, list(chain(*dbupd)))
	db.commit()
	return ret

