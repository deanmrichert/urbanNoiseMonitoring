''' 
	Script to monitor a sensor and save MQTT messages to an SQLite database.

	Author: Dean Richert
	Date: 31/10/2017
'''

import paho.mqtt.client as mqtt
import time
import json
import sqlite3
from shutil import copyfile
import os

client_name = "urbanNoiseMonitor" # must be unique to other instances of this script that are running simulataneously
broker = "tek-ns-us.thingsboard.io" 
topic = "app/#"
SIM_MODE = True

os.chdir('..')
if not os.path.isdir("data"):
	os.makedirs("data")
os.chdir("data")
	
conn = sqlite3.connect("acousticData_" + time.strftime("%Y_%m_%d_%Hh%Mm%Ss",time.localtime()) + ".db")
c = conn.cursor()

c.execute("create table sensor_msg (msg_id integer, deviceMetaData_deviceEUI text)")
c.execute("create table sensors (devEUI text, appEUI text, name text, lat real, lng real)")

msg_list = []

def on_connect(mqttc, obj, flags, rc):
	if rc == 0:
		mqttc.connected_flag = True
		print "connected ok"
	else:
		print "bad connection. returned code = " + rc

def on_subscribe(mqttc, obj, mid, granted_qos):
	mqttc.subscribed_flag = True
	print "subscribed ok"	

def on_message(mqttc, obj, msg):
	global msg_list
	msg_py = json.loads(msg.payload)
	msg_py["topic"] = msg.topic
	msg_py["qos"] = msg.qos
	print json.dumps(msg_py, sort_keys=True, indent=4, separators=(',', ': '))
	msg_list += [msg_py]
		
def add_dict(dict_to_add, key_prefix=''):
	for key, val in dict_to_add.iteritems():
		if isinstance(val,dict):
			if key == 'payloadMetaData':
				add_dict(val)
			else:
				add_dict(val,key_prefix + key + "_")
		elif isinstance(val,list):
			for (i,list_item) in zip(range(len(val)),val):
				add_dict(list_item,key_prefix + key + str(i) + "_")
		else:
			if not any(key_prefix + key in cols for cols in table_info):
				try:
					if int(val) is val:
						type = 'integer'
					else:
						type = 'real'
				except:
					type = 'text'
				c.execute("alter table sensor_msg add column " + key_prefix + key + " " + type)
			c.execute("update sensor_msg set " + key_prefix + key + " = '" + str(val) + "' where msg_id = " + str(msg_id))	
	
if __name__ == '__main__':
	
	# configure mqtt
	mqtt.Client.connected_flag = False
	mqtt.Client.subscribed_flag = False
	mqttc = mqtt.Client(client_name)
	mqttc.on_connect = on_connect # bind the call back functions
	mqttc.on_subscribe = on_subscribe
	mqttc.on_message = on_message
	mqttc.username_pw_set('XZgM9ZFk1sQ5MugP0JcE', password='OBjvT3xthKsHnAHEMXVF')
	
	# connect to broker
	print "connecting to broker " + broker
	try: 
		mqttc.connect(broker, 1883, 60) # connect to broker
	except:
		print "can't connect"
		sys.exit(1)
	mqttc.loop_start()
	while not mqttc.connected_flag:
		print "waiting for connection..."
		time.sleep(1)
	
	# subscribe to topic
	print "subscribing to topic " + topic	
	mqttc.subscribe(topic, 0)
	while not mqttc.subscribed_flag:
		print "waiting to subscribe..."
		time.sleep(1)
	
	# loop forever!
	num_msgs = 0
	try:
		while True:
			time.sleep(1)
			while msg_list != []:
				# update table info
				c.execute("pragma table_info(sensor_msg)")
				table_info = c.fetchall()
				# get devEUI
				try:
					devEUI = msg_list[0]["payloadMetaData"]["deviceMetaData"]["deviceEUI"]
					msg_list[0]["payloadMetaData"]["deviceMetaData"].pop("deviceEUI",None)
					appEUI = msg_list[0]["payloadMetaData"]["deviceMetaData"]["appEUI"]
					sensor_name = msg_list[0]["payloadMetaData"]["deviceMetaData"]["name"]
				except KeyError:
					devEUI = msg_list[0]["deviceMetaData"]["deviceEUI"]
					msg_list[0]["deviceMetaData"].pop("deviceEUI",None)
					appEUI = msg_list[0]["deviceMetaData"]["appEUI"]
					sensor_name = msg_list[0]["deviceMetaData"]["name"]
				if SIM_MODE:
					num_msgs += 1
					if num_msgs == 5:
						devEUI = "0000000000000000"
						appEUI = "FFFFFFFFFFFFFFFF"
						sensor_name = "this is a fake sensor"
					if num_msgs == 10:
						devEUI = "9999999999999999"
						appEUI = "AAAAAAAAAAAAAAAA"
						sensor_name = "this is another fake sensor!"
						num_msgs = 0
				# add to sensors table if it's a new device
				c.execute("select devEUI from sensors where devEUI = '" + devEUI + "'")
				if c.fetchone() is not None:
					# get msg id				
					c.execute("select max(msg_id) from sensor_msg where deviceMetaData_deviceEUI = '" + devEUI + "'")
					msg_id = c.fetchall()[0][0] + 1
				else:	
					c.execute("insert into sensors(devEUI, appEUI, name) values (?,?,?)",(devEUI,appEUI,sensor_name))
					msg_id = 0
				# add row to database
				c.execute("insert into sensor_msg(msg_id, deviceMetaData_deviceEUI) values (?,?)",(msg_id,devEUI))
				# add message to database
				add_dict(msg_list[0])
				conn.commit()
				# remove the processed message
				msg_list = msg_list[1:]
				
	except KeyboardInterrupt: # Ctrl-c to quit
		print "stopping client loop" 
		mqttc.loop_stop()
		print "disconnecting from broker " + broker
		mqttc.disconnect()
		conn.close()