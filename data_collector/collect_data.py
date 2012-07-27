import mindcontrol.userbrain as mc

import sqlite3
#from collections import defaultdict
import sys
import os
import datetime, time
from time import sleep
import collections

# DB STUFF
DB_NAME = 'user_data.db'
APPLICATION_NAME = 'Brainwave Collective'
def getDBConnection():
	return sqlite3.connect(os.path.join(os.getcwd(), DB_NAME))


table_names = (user, eeg, blink_event) = ('user', 'eeg', 'blink_event')
user_fields = (name, email_address, birthday, gender, registration_date) = ('name', 'email_address', 'birthday', 'gender', 'registration_date')
event_fields = (source, session_time, clock_time) = ('source', 'session_time', 'clock_time')
eeg_fields = event_fields + mc.brain_parameters
blinkStrength = 'blinkStrength'
blink_event_fields = event_fields + (blinkStrength,)
STRING_TYPE = (name, email_address, gender, birthday, registration_date,session_time, clock_time)
INT_TYPE = (blinkStrength, source)
REAL_TYPE = (eeg_fields,)



TABLE_CREATION_TEMPLATE = 'CREATE TABLE IF NOT EXISTS %s (%s)'
DATA_INSERT_TEMPLATE = 'INSERT INTO %s VALUES(%s)'
	

def getUserInfo(username):
	print 'Hello %s! Welcome to the %s application suite. You will now supply the information required to register you as a new user of the system.' % (username, APPLICATION_NAME)
	email = raw_input('Email Address: ')
	print 'now birthday. Please enter your birth date below in the format below.'
	burfday = raw_input('MM/DD/YYYY: ')
	sex = raw_input('Gender. Enter M for male and F for female: ')
	reg_date = datetime.datetime.now()
	print 'Thank you. The information obtained from you is as follows:'
	info_dict = {name:username, email_address:email, birthday: burfday, gender:sex, registration_date:reg_date}
	for (k, v) in info_dict.items():
		print '\tk: %s\tv: %s' % (k, v)
	return info_dict



def determine_table(data):
	if blinkStrength in data:
		return blink_event
	elif 'attention' in data:
		return eeg
	else:
		return None


def load_user(username):
	# try to select from db
	con = getDBConnection()
	with con:
		stmt = 'SELECT uid FROM user WHERE name="%s"' % username
		cur = con.cursor()
		cur.execute(stmt)
		con.commit()
		row = cur.fetchone()
		return sum(row) if isinstance(row, collections.Iterable) else row

def createNewUser(username, numUsers):
	
	user_info = getUserInfo(username)
	dbc = getDBConnection()
	with dbc:
		cur = dbc.cursor()
		stmt = 'INSERT INTO user VALUES(?, ?, ?, ?, ?, ?)'
		cur.execute( stmt, [numUsers+1,] + [ str(user_info[x]) for x in user_fields ] )
		dbc.commit()
		sel_stmt = 'SELECT uid FROM user WHERE name="%s"' % user_info[name]
		cur.execute(sel_stmt)
		dbc.commit()
		row = cur.fetchone()
		return sum(row) if isinstance(row, collections.Iterable) else row


def _getSQLType(field_name):
	if field_name in STRING_TYPE:
		return 'TEXT'
	elif field_name in INT_TYPE:
		return 'INTEGER'
	else:
		return 'REAL'
	

def build_headers(fields):
	hdr_list = list()
	src_in_fields = False
	for f in fields:
		if f == name:
			hdr_list.append(('uid', 'INTEGER PRIMARY KEY AUTOINCREMENT'))
		hdr_list.append((f, _getSQLType(f)))
		if f == source:
			src_in_fields = True
	if src_in_fields:
		hdr_list.append(('FOREIGN KEY(source) REFERENCES', 'user(uid)'))
	return ', '.join([ '%s %s' % x for x in hdr_list])


def buildCreateTableStatement(tableName, fields):
	args = build_headers(fields)
	return TABLE_CREATION_TEMPLATE % (tableName, args)


LOGON_MESSAGE = 'Enter your username (one will be created if it doesn\'t exist): '
def handleLogin(numUsers):
	entered_username = raw_input(LOGON_MESSAGE)
	loaded_user = load_user(entered_username)
	if not loaded_user:
		loaded_user = createNewUser(entered_username, numUsers)
	return loaded_user


def initializeDB():
	nameToValues = {user:user_fields, eeg:eeg_fields, blink_event:blink_event_fields}
	con = getDBConnection()
	with con:
		cur = con.cursor()
		for t in table_names:
			stmt = buildCreateTableStatement(t, nameToValues[t])
			cur.execute(stmt)
			con.commit()
		# now get all the users
		cur.execute('SELECT * FROM user')
		con.commit()
		all_users = cur.fetchall()
	return len(all_users)



def processData(data, current_uid, session_start_time):
	con = None
	try:
		con = getDBConnection()
		cur = con.cursor()
		# determining table
		table_name = determine_table(data)
		#if table_name == eeg:
		#	print 'FINALLY GOT ONE WOOO!'
		#print data
		#print table_name
		if not table_name:
			return
		# now populate the event metadata
		src = current_uid
		clock_time = datetime.datetime.now()
		session_time = clock_time - session_start_time
		meta_vals = [src, session_time, clock_time]
		# now figure out the headset data layout
		#print data
		vals = []
		if table_name == blink_event:
			vals.append(data[blinkStrength])
		if table_name == eeg:
			vals.extend([ str(data[x]) for x in mc.brain_parameters])
		
		
		#print vals
		if len(vals) < 1:
			return
		meta_vals.extend(vals)
		stmt = DATA_INSERT_TEMPLATE % (table_name, ', '.join(['?'] * len(meta_vals)))
		#print 'statement: %s' % stmt
		#print 'meta vals: %s' % meta_vals
		cur.execute(stmt, [str(x) for x in meta_vals])
		con.commit()
	finally:
		if con:
			con.close()

DEBUG_MODE = False
SESSION_DURATION = 2 # minutes
MAX_DATA = 1500

def main():
	data_count = 0
	ds = mc._datastream(lambda: True )
	numUsers = initializeDB()
	
	user = handleLogin(numUsers) if not DEBUG_MODE else 1 # my ID
	
	
	session_start_time = None
	done_connecting = False
	
	for d in ds:
		if d == mc.NULL_DATA:
			print 'Connecting...'
		else:
			if not done_connecting:
				done_connecting = True
				print 'Connected to the brain. beginning data collection'
				session_start_time = datetime.datetime.now()
			processData(d, user, session_start_time)
			data_count += 1
	
	print 'Exiting program'

if __name__ == '__main__':
	main()
	
