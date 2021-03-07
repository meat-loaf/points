The only dependecny is Flask. Run pip3 install -r requirements.txt
Run with python3 ./main.py. Binds to localhost:9001
uses the sqlite3 package shipped with python to store data in a database named database.db.

Endpoints are as follows, required payload (if any) immediately follows:

* /points/<payer name>/add [post]
	* {"points": <num points>, "timestamp": <timestamp>}
Add points for a payer. If the payer doesn't exist, it is added.
Response is a list of all payers added and their allocated points:
	* [{"payer": <payer name>, "points": <payer points>},
	   {"payer": <payer name>, "points": <payer points>},
	   ...
	  ]
Payers with 0 points are also returned.

* /points/ [get]
* /points/<payer name> [get]
Get the number of available points for all payers or for a single payer, respectively

* /points/spend [post]
	* {"points": <num points>}
Spend points against the total pool.
Response is a list of the points spent for each user:
	* [{"payer": <payer name>, "points": <payer points>},
	   {"payer": <payer name>, "points": <payer points>},
	   ...
	  ]
<payer points> will be negative, or 0

Notes:
	No concept of users: points are spent from a global pool and that's it.
	The database schema allocates tables to track what points were spent
	by what users, however. There is also a default user (admin) and a route to spend points for a specific user (/points/spend/<user>) but the user parameter is ignored.
	There is an interesting situation where points can be added with a timestamp earlier than points that were spent, creating a situation where the points effecively 'should' have been spent but were not. Should this be allowed? I didn't do any work to check against this; further 'spends' will still spend these points first, so it balances out eventually.
	The timestamp format isn't consistent, nor is it enforced. Timestamp checking is very lazy, so different timestamp formats will break the sorting logic for points spendng.
