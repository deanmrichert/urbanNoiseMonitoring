#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import random
import numpy as np
import sqlite3
import struct 
import warnings
import time
import os.path

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from PyQt4 import QtNetwork
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.colors import LogNorm
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

warnings.filterwarnings("ignore",category=FutureWarning) # matplotlib known bug
warnings.filterwarnings('error',category=RuntimeWarning)

def R_A(f):
	rv = 12194**2*f**4
	rv /= f**2+20.6**2
	rv /= np.sqrt((f**2+107.7**2)*(f**2+737.9**2))
	rv /= f**2+12194**2
	return rv

def A(f):
	return 20*np.log10(R_A(f)) + 2.0
	
freqs = range(-5,7)
freqs = [1e3*2**f for f in freqs]
		
html = '''
		<!DOCTYPE html>
		<html>
  <head>
	<meta name="viewport" content="initial-scale=1.0, user-scalable=no">
	<meta charset="utf-8">
	<title>Acoustic Sensor Map</title>
	<style>
	  /* Always set the map height explicitly to define the size of the div
	   * element that contains the map. */
	  #map {
		height: 100%;
		width: 100%;
	  }
	  /* Optional: Makes the sample page fill the window. */
	  html, body {
		height: 100%;
		width: 100%;
		margin: 0;
		padding: 0;
	  }
	</style>
  </head>
  <body>
	<div id="map"></div>
	<script>	
		var map;
		var markers = [];
		var activeMarker;
		var green_marker = "http://maps.google.com/mapfiles/ms/icons/green-dot.png";
		var red_marker = "http://maps.google.com/mapfiles/ms/icons/red-dot.png";
		function initMap() {
			map = new google.maps.Map(document.getElementById('map'), {
			  zoom: 13,
			  center: {lat: 51.046056, lng: -114.057352} // city hall
			});
		}
		
		function createMarker(sensor_lat, sensor_lng, sensor_name, sensor_eui) {
			if (typeof activeMarker != "undefined") { 
				activeMarker.setIcon(red_marker);
			};
			var marker = new google.maps.Marker({
				map: map,
				position: {lat: sensor_lat, lng: sensor_lng},
				icon: green_marker,
				title: sensor_name,
				devEUI: sensor_eui,
			});
			activeMarker = marker;
			marker.addListener('click', setActiveMarker_fromJs);
			markers.push(marker);
		}
	
		function setActiveMarker_fromJs(evt) {
			if (activeMarker != this) {
				if (typeof activeMarker != "undefined") { 
					activeMarker.setIcon(red_marker);
				};
				activeMarker = this; 
				activeMarker.setIcon(green_marker);
				self.setActiveSensor(activeMarker.devEUI);
			};
		}
		
		function setActiveMarker_fromPy(devEUI) {
			if (typeof activeMarker != "undefined") { 
				activeMarker.setIcon(red_marker);
			};
			for (var i = 0; i < markers.length; i++) {
				if (markers[i].devEUI == devEUI) {
					activeMarker = markers[i];
					activeMarker.setIcon(green_marker);
				};
			};
		}
		
		function removeMarker(devEUI) {
			for (var i = 0; i < markers.length; i++) {
				if (markers[i].devEUI == devEUI) {
					markers[i].setMap(null);
					markers.splice(i,1);
				};
			};
		}
		
		function removeAllMarkers() {
			for (var i = 0; i < markers.length; i++) {
				markers[i].setMap(null);
			};
			markers = []
		}
		
		function setMarkerLocation(sensor_lat, sensor_lng){
			activeMarker.setPosition({lat: sensor_lat, lng: sensor_lng});
		}
		
		function centerMap_atCentroid(){
			if (markers.length > 0) {
				var map_center_lat = 0.0;
				var map_center_lng = 0.0;
				for (var i = 0; i < markers.length; i++) {
					map_center_lat = map_center_lat + markers[i].getPosition().lat();
					map_center_lng = map_center_lng + markers[i].getPosition().lng();
				};
				map_center_lat = map_center_lat/markers.length;
				map_center_lng = map_center_lng/markers.length;
			
				map.setCenter({lat: map_center_lat, lng: map_center_lng});
			} else {
				map.setCenter({lat: 51.046056, lng: -114.057352});
			};
		}
		
		function centerMap(sensor_lat, sensor_lng){
			map.setCenter({lat: sensor_lat, lng: sensor_lng});
			map.setZoom(17);
		}
	</script>
	<script async defer
	src="https://maps.googleapis.com/maps/api/js?v=3&key=AIzaSyApzTegXjQBsmc3uNSu8yPxWVxSSJqMYeY&callback=initMap">
	</script>
  </body>
</html>
'''

class PicButton(QAbstractButton):
	def __init__(self, lock, lock_hover, unlock, unlock_hover, update_locks):
		super(PicButton, self).__init__()
		
		self.update_locks = update_locks
		
		self.lock = lock
		self.lock_hover = lock_hover
		self.unlock = unlock
		self.unlock_hover = unlock_hover
		
		self.pixmap = self.unlock
		self.pixmap_hover = self.lock_hover
		self.pixmap_pressed = self.lock
		
		self.locked = False
		self.enabled = False
		
	def paintEvent(self, event):
		if self.underMouse():
			pix = self.pixmap_hover
		else:
			pix = self.pixmap 
		if self.isDown():
			pix = self.pixmap_pressed

		painter = QPainter(self)
		painter.drawPixmap(event.rect(), pix)

	def sizeHint(self):
		return QSize(15,15)
		
	def mouseReleaseEvent(self,event):
		super(PicButton, self).mouseReleaseEvent(event)
		if self.enabled:
			posMouse =	event.pos()
			if self.rect().contains(posMouse):
				self.locked = not self.locked 
				if self.update_locks() and self.locked:
					self.pixmap = self.lock
					self.pixmap_hover = self.unlock_hover
					self.pixmap_pressed = self.unlock
				else:	
					self.pixmap = self.unlock
					self.pixmap_hover = self.lock_hover
					self.pixmap_pressed = self.lock
					self.locked = False
	
	def setLock(self):
		self.locked = True
		if self.update_locks():
			self.pixmap = self.lock
			self.pixmap_hover = self.unlock_hover
			self.pixmap_pressed = self.unlock
		else:
			self.locked = False
		self.update()
	
	def setEnabled(self, enable):
		self.enabled = enable
				
class Window(QWidget):
	def __init__(self):
		super(Window, self).__init__()
		
		####
		
		self.setWindowTitle("Urban Noise Monitor")
		self.setWindowIcon(QIcon('figures\CityOfCalgarylogo.png'))
		
		####
		
		database_groupBox = QGroupBox("Database")
		#
		database_file = QLabel('File path:')
		self.database_fileEdit = QLineEdit()
		self.browse_button = QPushButton("Browse")
		self.browse_button.clicked.connect(self.selectFile)
		self.load_button = QPushButton("Load")
		self.load_button.clicked.connect(self.load_database)
		#
		database_layout = QHBoxLayout()
		#
		database_layout.addWidget(database_file)
		database_layout.addWidget(self.database_fileEdit)
		database_layout.addWidget(self.browse_button)
		database_layout.addWidget(self.load_button)
		#
		database_groupBox.setLayout(database_layout)
		
		####
		
		map_groupBox = QGroupBox("Sensor map")
		#
		self.gmap_webView = QWebView(self)
		self.gmap_webView.page().mainFrame().addToJavaScriptWindowObject('self', self)
		self.gmap_webView.setHtml(html)
		self.gmap_webView.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
		#
		map_layout = QVBoxLayout()
		#
		map_layout.addWidget(self.gmap_webView)
		#
		map_groupBox.setLayout(map_layout)
		
		####

		sensor_groupBox = QGroupBox("Sensor information")
		#
		sensor_devEui = QLabel('Device EUI')
		self.sensor_devEui_comboBox = QComboBox(self)
		self.sensor_devEui_comboBox.activated[str].connect(self.setActiveSensor)
		sensor_name = QLabel('Name')
		self.sensor_nameEdit = QLineEdit()
		self.sensor_nameEdit.setReadOnly(True)
		self.sensor_nameEdit.setDisabled(True)
		sensor_appEui = QLabel('Application EUI')
		self.sensor_appEuiEdit = QLineEdit()
		self.sensor_appEuiEdit.setReadOnly(True)
		self.sensor_appEuiEdit.setDisabled(True)
		sensor_location = QLabel('Location')
		self.sensor_locationEdit = QLineEdit()
		self.sensor_locationEdit.setPlaceholderText("lat,lng")
		self.sensor_locationEdit.returnPressed.connect(self.update_sensor_location)
		self.sensor_locationEdit.setReadOnly(True)
		self.sensor_locationEdit.setDisabled(True)
		self.goto_loc_button = QPushButton("Go")
		self.goto_loc_button.setMinimumWidth(30)
		self.goto_loc_button.clicked.connect(self.goto_location)
		self.goto_loc_button.setEnabled(False)
		#
		sensor_grid = QGridLayout()
		#
		sensor_grid.setColumnStretch(0,5)
		sensor_grid.setColumnMinimumWidth(0,1)
		sensor_grid.setColumnStretch(1,10)
		sensor_grid.setColumnMinimumWidth(1,1)
		sensor_grid.setColumnStretch(2,1)
		sensor_grid.setColumnMinimumWidth(2,1)
		#
		sensor_grid.addWidget(sensor_devEui,0,0)
		sensor_grid.addWidget(self.sensor_devEui_comboBox,0,1,1,2)
		sensor_grid.addWidget(sensor_name,1,0)
		sensor_grid.addWidget(self.sensor_nameEdit,1,1,1,2)
		sensor_grid.addWidget(sensor_appEui,2,0)
		sensor_grid.addWidget(self.sensor_appEuiEdit,2,1,1,2)
		sensor_grid.addWidget(sensor_location,3,0)
		sensor_grid.addWidget(self.sensor_locationEdit,3,1)
		sensor_grid.addWidget(self.goto_loc_button,3,2)
		#
		sensor_groupBox.setLayout(sensor_grid)
		
		####

		message_groupBox = QGroupBox("Message information")
		#
		message_id = QLabel('Message ID')
		self.message_idEdit = QLineEdit()
		self.message_idEdit.setReadOnly(True)
		self.message_id_sqlEdit = QLineEdit()
		self.message_id_lock = PicButton(QPixmap("figures\lock.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\lock_hover.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\unlock.png").scaledToWidth(15, mode=Qt.SmoothTransformation), QPixmap("figures\unlock_hover.png").scaledToWidth(15, mode=Qt.SmoothTransformation),self.update_locks)
		message_fcount = QLabel('Frame count')
		self.message_fcountEdit = QLineEdit()
		self.message_fcountEdit.setReadOnly(True)
		self.message_fcount_sqlEdit = QLineEdit()
		self.message_fcount_lock = PicButton(QPixmap("figures\lock.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\lock_hover.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\unlock.png").scaledToWidth(15, mode=Qt.SmoothTransformation), QPixmap("figures\unlock_hover.png").scaledToWidth(15, mode=Qt.SmoothTransformation),self.update_locks)
		message_payload = QLabel('Payload')
		self.message_payloadEdit = QLineEdit()
		self.message_payloadEdit.setReadOnly(True)
		self.message_payload_sqlEdit = QLineEdit()
		self.message_payload_lock = PicButton(QPixmap("figures\lock.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\lock_hover.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\unlock.png").scaledToWidth(15, mode=Qt.SmoothTransformation), QPixmap("figures\unlock_hover.png").scaledToWidth(15, mode=Qt.SmoothTransformation),self.update_locks)
		message_topic = QLabel('Topic')
		self.message_topicEdit = QLineEdit()
		self.message_topicEdit.setReadOnly(True)
		self.message_topic_sqlEdit = QLineEdit()
		self.message_topic_lock = PicButton(QPixmap("figures\lock.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\lock_hover.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\unlock.png").scaledToWidth(15, mode=Qt.SmoothTransformation), QPixmap("figures\unlock_hover.png").scaledToWidth(15, mode=Qt.SmoothTransformation),self.update_locks)
		message_time = QLabel('Time')
		self.message_timeEdit = QLineEdit()
		self.message_timeEdit.setReadOnly(True)
		self.message_time_sqlEdit = QLineEdit()
		self.message_time_lock = PicButton(QPixmap("figures\lock.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\lock_hover.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\unlock.png").scaledToWidth(15, mode=Qt.SmoothTransformation), QPixmap("figures\unlock_hover.png").scaledToWidth(15, mode=Qt.SmoothTransformation),self.update_locks)
		message_gateway_name = QLabel('Gtwy name')
		self.message_gateway_nameEdit = QLineEdit()
		self.message_gateway_nameEdit.setReadOnly(True)
		self.message_gateway_name_sqlEdit = QLineEdit()
		self.message_gateway_name_lock = PicButton(QPixmap("figures\lock.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\lock_hover.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\unlock.png").scaledToWidth(15, mode=Qt.SmoothTransformation), QPixmap("figures\unlock_hover.png").scaledToWidth(15, mode=Qt.SmoothTransformation),self.update_locks)
		message_gateway_mac = QLabel('Gtwy MAC')
		self.message_gateway_macEdit = QLineEdit()
		self.message_gateway_macEdit.setReadOnly(True)
		self.message_gateway_mac_sqlEdit = QLineEdit()
		self.message_gateway_mac_lock = PicButton(QPixmap("figures\lock.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\lock_hover.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\unlock.png").scaledToWidth(15, mode=Qt.SmoothTransformation), QPixmap("figures\unlock_hover.png").scaledToWidth(15, mode=Qt.SmoothTransformation),self.update_locks)
		message_gateway_loc = QLabel('Gtwy location')
		self.message_gateway_locEdit = QLineEdit()
		self.message_gateway_locEdit.setReadOnly(True)
		self.message_gateway_loc_sqlEdit = QLineEdit()
		self.message_gateway_loc_lock = PicButton(QPixmap("figures\lock.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\lock_hover.png").scaledToWidth(15,mode=Qt.SmoothTransformation),QPixmap("figures\unlock.png").scaledToWidth(15, mode=Qt.SmoothTransformation), QPixmap("figures\unlock_hover.png").scaledToWidth(15, mode=Qt.SmoothTransformation),self.update_locks)
		self.first_button = QPushButton("<<")
		self.first_button.setMinimumWidth(30)
		self.first_button.clicked.connect(self.first_msg)
		self.prev_button = QPushButton("<")
		self.prev_button.setMinimumWidth(30)
		self.prev_button.clicked.connect(self.prev_msg)
		self.message_indexEdit = QLineEdit()
		self.message_indexEdit.setMinimumWidth(30)
		self.message_indexEdit.returnPressed.connect(self.update_msg_idx)
		self.next_button = QPushButton(">")
		self.next_button.setMinimumWidth(30)
		self.next_button.clicked.connect(self.next_msg)
		self.last_button = QPushButton(">>")
		self.last_button.setMinimumWidth(30)
		self.last_button.clicked.connect(self.last_msg)
		
		#
		message_grid = QGridLayout()
		#
		message_grid.setColumnStretch(0,10)
		message_grid.setColumnMinimumWidth(0,1)
		message_grid.setColumnStretch(1,10)
		message_grid.setColumnMinimumWidth(1,1)
		message_grid.setColumnStretch(2,10)
		message_grid.setColumnMinimumWidth(2,1)
		message_grid.setColumnStretch(3,10)
		message_grid.setColumnMinimumWidth(3,1)
		message_grid.setColumnStretch(4,10)
		message_grid.setColumnMinimumWidth(4,1)
		message_grid.setColumnStretch(5,1)
		message_grid.setColumnMinimumWidth(5,1)
		#
		message_grid.addWidget(message_id,0,0)
		message_grid.addWidget(self.message_idEdit,0,1,1,2)
		message_grid.addWidget(self.message_id_sqlEdit,0,3,1,2)
		message_grid.addWidget(self.message_id_lock,0,5)
		message_grid.addWidget(message_topic,1,0)
		message_grid.addWidget(self.message_topicEdit,1,1,1,2)
		message_grid.addWidget(self.message_topic_sqlEdit,1,3,1,2)
		message_grid.addWidget(self.message_topic_lock,1,5)
		message_grid.addWidget(message_time,2,0)
		message_grid.addWidget(self.message_timeEdit,2,1,1,2)
		message_grid.addWidget(self.message_time_sqlEdit,2,3,1,2)
		message_grid.addWidget(self.message_time_lock,2,5)
		message_grid.addWidget(message_payload,3,0)
		message_grid.addWidget(self.message_payloadEdit,3,1,1,2)
		message_grid.addWidget(self.message_payload_sqlEdit,3,3,1,2)
		message_grid.addWidget(self.message_payload_lock,3,5)
		message_grid.addWidget(message_fcount,4,0)
		message_grid.addWidget(self.message_fcountEdit,4,1,1,2)
		message_grid.addWidget(self.message_fcount_sqlEdit,4,3,1,2)
		message_grid.addWidget(self.message_fcount_lock,4,5)
		message_grid.addWidget(message_gateway_name,5,0)
		message_grid.addWidget(self.message_gateway_nameEdit,5,1,1,2)
		message_grid.addWidget(self.message_gateway_name_sqlEdit,5,3,1,2)
		message_grid.addWidget(self.message_gateway_name_lock,5,5)
		message_grid.addWidget(message_gateway_mac,6,0)
		message_grid.addWidget(self.message_gateway_macEdit,6,1,1,2)
		message_grid.addWidget(self.message_gateway_mac_sqlEdit,6,3,1,2)
		message_grid.addWidget(self.message_gateway_mac_lock,6,5)
		message_grid.addWidget(message_gateway_loc,7,0)
		message_grid.addWidget(self.message_gateway_locEdit,7,1,1,2)
		message_grid.addWidget(self.message_gateway_loc_sqlEdit,7,3,1,2)
		message_grid.addWidget(self.message_gateway_loc_lock,7,5)
		message_grid.addWidget(self.first_button,8,0)
		message_grid.addWidget(self.prev_button,8,1)
		message_grid.addWidget(self.message_indexEdit,8,2)
		message_grid.addWidget(self.next_button,8,3)
		message_grid.addWidget(self.last_button,8,4)
		#
		message_groupBox.setLayout(message_grid)
		
		####
		
		self.plotType = QComboBox(self)
		self.plotType.addItem("Raw data")
		self.plotType.addItem("dBA")
		self.plotType.addItem("dBZ")
		self.plotType.addItem("Spectrogram (dBZ)")
		self.plotType.addItem("Spectrogram (dBA)")
		self.plotType.activated[str].connect(self.plot)
		
		####
		
		self.plt_widget = QDialog(self)
		self.plt_widget.figure = Figure()
		self.plt_widget.figure.set_facecolor('white')
		self.plt_widget.canvas = FigureCanvas(self.plt_widget.figure)
		
		####
		
		grid = QGridLayout()
		#
		grid.setColumnStretch(0,2)
		grid.setColumnStretch(1,1)
		grid.setRowStretch(0,0.5)
		grid.setRowStretch(1,1)
		grid.setRowStretch(2,2)
		grid.setRowStretch(3,0.1)
		grid.setRowStretch(4,2)
		#
		
		grid.addWidget(database_groupBox,0,0,1,2)
		grid.addWidget(map_groupBox,1,0,2,1)
		#grid.addWidget(self.gmap_webView,1,0,3,1)
		grid.addWidget(sensor_groupBox,1,1)	
		grid.addWidget(message_groupBox,2,1)	
		grid.addWidget(self.plotType,3,0,1,2)
		grid.addWidget(self.plt_widget.canvas,4,0,1,2)
		#
		self.setLayout(grid)
		
		####
		
		self.enableWidgets(False)
		self.showMaximized()
		####
		
		self.activeSensorIdx = 0
		self.activeMsgIdx = 0
		self.num_msgs = 0
		self.sensors = []
		self.conn = None # sqlite connection
		self.c = None # sqlite cursor
		self.search_filters = ''
		self.timer = QTimer()
		self.timer.timeout.connect(self.update_gui)
		self.activeSensorHasLoc = False
	
	@pyqtSlot(str)	
	def setActiveSensor(self, devEUI):
		self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("setActiveMarker_fromPy('" + devEUI + "')"))
		for idx in range(len(self.sensors)):
			if self.sensors[idx][0] == devEUI:
				if self.activeSensorIdx == idx:
					return
				self.activeSensorIdx = idx
				break
		if self.sensors[self.activeSensorIdx][3] != 'None' and self.sensors[self.activeSensorIdx][3] is not None and self.sensors[self.activeSensorIdx][4] != 'None' and self.sensors[self.activeSensorIdx][4] is not None:
			self.activeSensorHasLoc = True
		else:
			self.activeSensorHasLoc = False
		self.c.execute("select msg_id from sensor_msg where deviceMetaData_deviceEUI = '" + str(self.sensors[self.activeSensorIdx][0]) + "'" + self.search_filters + " order by msg_id asc")
		self.valid_msg_ids = [id[0] for id in self.c.fetchall()]
		self.num_msgs = len(self.valid_msg_ids)
		self.last_msg()
		self.update_sensor_info()
		self.plot(str(self.plotType.currentText()))
		self.sensor_devEui_comboBox.setCurrentIndex(self.activeSensorIdx) 
	
	def plot(self, text):
		if text == 'dBA':
			self.plot_dBA()
		elif text == 'Raw data':
			self.plot_raw()
		elif text == 'dBZ':
			self.plot_dBZ()
		elif text == 'Spectrogram (dBA)':
			self.plot_spec_dBA()
		elif text == 'Spectrogram (dBZ)':
			self.plot_spec_dBZ()
	
	def plot_raw(self):
		self.c.execute("select msg_id, payload from sensor_msg where deviceMetaData_deviceEUI = '" + self.sensors[self.activeSensorIdx][0] + "' and payload is not null" + self.search_filters + " order by msg_id asc")
		tmp = self.c.fetchall()
		y_data = []
		x_data = []
		for data in tmp:
			x_data += [data[0]]
			hex_rep = data[1].decode('base64').encode('hex')
			y_data += [[]]
			while len(hex_rep) > 8:
				y_data[-1] += [struct.unpack('!f', hex_rep[0:8].decode('hex'))[0]]
				hex_rep = hex_rep[8:]
		self.plt_widget.figure.clf()
		ax = self.plt_widget.figure.add_subplot(111)
		ax.set_ylabel('Raw data (dB)')
		ax.set_xlabel('Message ID')
		plt_handle = ax.plot(x_data,y_data, '*-')
		ax.legend(plt_handle,[str(f) + "Hz" for f in freqs[0:len(y_data[0])]])
		ax.set_aspect('auto')
		self.plt_widget.figure.tight_layout()
		self.plt_widget.canvas.draw()
		self.plotType.setCurrentIndex(0)

	def plot_dBA(self):
		self.c.execute("select msg_id, payload from sensor_msg where deviceMetaData_deviceEUI = '" + self.sensors[self.activeSensorIdx][0] + "' and payload is not null" + self.search_filters + " order by msg_id asc")
		tmp = self.c.fetchall()
		y_data = []
		x_data = []
		for data in tmp:
			hex_rep = data[1].decode('base64').encode('hex')
			dBA = 0.0
			j = 0
			while len(hex_rep) > 8:
				dBA += 10**((struct.unpack('!f', hex_rep[0:8].decode('hex'))[0] + A(freqs[j]))/10)
				hex_rep = hex_rep[8:]
				j += 1
			try:
				y_data += [10*np.log10(dBA)]
				x_data += [data[0]]
			except RuntimeWarning:
				pass
		self.plt_widget.figure.clf()
		ax = self.plt_widget.figure.add_subplot(111)
		ax.set_ylabel('Sound Pressure Level (dBA)')
		ax.set_xlabel('Message ID')
		ax.plot(x_data,y_data, '*-')
		ax.set_aspect('auto')
		self.plt_widget.figure.tight_layout()
		self.plt_widget.canvas.draw()
		self.plotType.setCurrentIndex(1) 
		
	def plot_dBZ(self):
		self.c.execute("select msg_id, payload from sensor_msg where deviceMetaData_deviceEUI = '" + self.sensors[self.activeSensorIdx][0] + "' and payload is not null" + self.search_filters + " order by msg_id asc")
		tmp = self.c.fetchall()
		y_data = []
		x_data = []
		for data in tmp:
			hex_rep = data[1].decode('base64').encode('hex')
			dBZ = 0.0
			j = 0
			while len(hex_rep) > 8:
				dBZ += 10**((struct.unpack('!f', hex_rep[0:8].decode('hex'))[0])/10)
				hex_rep = hex_rep[8:]
				j += 1
			try:
				y_data += [10*np.log10(dBZ)]
				x_data += [data[0]]
			except RuntimeWarning:
				pass
		self.plt_widget.figure.clf()
		ax = self.plt_widget.figure.add_subplot(111)
		ax.set_ylabel('Sound Pressure Level (dBZ)')
		ax.set_xlabel('Message ID')
		ax.plot(x_data,y_data, '*-')
		ax.set_aspect('auto')
		self.plt_widget.figure.tight_layout()
		self.plt_widget.canvas.draw()
		self.plotType.setCurrentIndex(2) 
	
	def plot_spec_dBZ(self):
	
		self.c.execute("select msg_id, payload from sensor_msg where deviceMetaData_deviceEUI = '" + self.sensors[self.activeSensorIdx][0] + "' and payload is not null" + self.search_filters + " order by msg_id asc")
		tmp = self.c.fetchall()
		y_data = []
		x_data = []
		for data in tmp:
			x_data += [data[0]]
			hex_rep = data[1].decode('base64').encode('hex')
			y_data += [[]]
			while len(hex_rep) > 8:
				y_data[-1] += [struct.unpack('!f', hex_rep[0:8].decode('hex'))[0]]
				hex_rep = hex_rep[8:]
		self.plt_widget.figure.clf()
		ax = self.plt_widget.figure.add_subplot(111)
		ax.set_ylabel('Octave Band (Hz)')
		ax.set_xlabel('Message ID')
		_,y = np.shape(y_data)
		X,Y=np.meshgrid(x_data,freqs[0:y+1])
		im = ax.pcolormesh(X,Y,np.transpose(y_data))
		ax.set_yscale('log')
		ax.set_xlim([x_data[0],x_data[-1]])
		ax.set_ylim([freqs[0],freqs[y]])
		ax.set_aspect('auto')
		cbar = self.plt_widget.figure.colorbar(im, orientation='vertical')
		cbar.set_label('dBZ')
		self.plt_widget.figure.tight_layout()
		self.plt_widget.canvas.draw()
		self.plotType.setCurrentIndex(3)
		
	def plot_spec_dBA(self):
	
		self.c.execute("select msg_id, payload from sensor_msg where deviceMetaData_deviceEUI = '" + self.sensors[self.activeSensorIdx][0] + "' and payload is not null" + self.search_filters + " order by msg_id asc")
		tmp = self.c.fetchall()
		y_data = []
		x_data = []
		for data in tmp:
			x_data += [data[0]]
			hex_rep = data[1].decode('base64').encode('hex')
			y_data += [[]]
			j = 0
			while len(hex_rep) > 8:
				y_data[-1] += [struct.unpack('!f', hex_rep[0:8].decode('hex'))[0] + A(freqs[j])]
				hex_rep = hex_rep[8:]
				j += 1
		self.plt_widget.figure.clf()
		ax = self.plt_widget.figure.add_subplot(111)
		ax.set_ylabel('Octave Band (Hz)')
		ax.set_xlabel('Message ID')
		_,y = np.shape(y_data)
		X,Y=np.meshgrid(x_data,freqs[0:y+1])
		im = ax.pcolormesh(X,Y,np.transpose(y_data))
		ax.set_yscale('log')
		ax.set_xlim([x_data[0],x_data[-1]])
		ax.set_ylim([freqs[0],freqs[y]])
		ax.set_aspect('auto')
		cbar = self.plt_widget.figure.colorbar(im, orientation='vertical')
		cbar.set_label('dBZ')
		self.plt_widget.figure.tight_layout()
		self.plt_widget.canvas.draw()
		self.plotType.setCurrentIndex(4)
	
	def load_database(self):
		self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("removeAllMarkers()"))
		if os.path.isfile(str(self.database_fileEdit.text())):
			try:
				self.conn = sqlite3.connect(str(self.database_fileEdit.text()))
				self.c = self.conn.cursor()
				self.c.execute("select * from sensors")
				self.sensors = self.c.fetchall()
							
				self.enableWidgets(True)
				self.search_filters = ''
				
				for sensor in self.sensors:
					self.sensor_devEui_comboBox.addItem(sensor[0])
					if sensor[3] != 'None' and sensor[3] is not None and sensor[4] != 'None' and sensor[4] is not None:
						self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("createMarker(" + str(sensor[3]) + "," + str(sensor[4]) + ",'" + sensor[2] + "','" + sensor[0] + "')"))
				
				self.c.execute("select max(msg_id) from sensor_msg where deviceMetaData_deviceEUI = '" + str(self.sensors[self.activeSensorIdx][0]) + "'")
				
				self.message_id_sqlEdit.setText(">= " + str(max([0,self.c.fetchone()[0]-100])))
				self.message_id_lock.setLock()
				
				self.activeSensorIdx = -1;
				self.setActiveSensor(self.sensors[0][0])
			
				self.timer.start(5000) #trigger every 5 seconds
			except:
				self.enableWidgets(False)
				self.timer.stop()
		else:
			self.enableWidgets(False)
			self.timer.stop()
		self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("centerMap_atCentroid()"))
	
	def selectFile(self):
		self.database_fileEdit.setText(QFileDialog.getOpenFileName())
	
	def first_msg(self):
		self.activeMsgIdx = 0
		if self.activeMsgIdx >= self.num_msgs-1:
			self.next_button.setEnabled(False)
			self.last_button.setEnabled(False)
		else: 
			self.last_button.setEnabled(True)
			self.next_button.setEnabled(True)
		self.first_button.setEnabled(False)
		self.prev_button.setEnabled(False)
		self.message_indexEdit.setText(str(self.activeMsgIdx))
		self.update_msg_info()
	
	def next_msg(self):
		self.activeMsgIdx += 1
		if self.activeMsgIdx >= self.num_msgs-1:
			self.next_button.setEnabled(False)
			self.last_button.setEnabled(False)
		else: 
			self.next_button.setEnabled(True)
			self.last_button.setEnabled(True)
		if self.activeMsgIdx <= 0:
			self.prev_button.setEnabled(False)
			self.first_button.setEnabled(False)
		else:
			self.prev_button.setEnabled(True)
			self.first_button.setEnabled(True)
		self.message_indexEdit.setText(str(self.activeMsgIdx))
		self.update_msg_info()
	
	def prev_msg(self):
		self.activeMsgIdx -= 1
		if self.activeMsgIdx >= self.num_msgs-1:
			self.next_button.setEnabled(False)
			self.last_button.setEnabled(False)
		else:
			self.next_button.setEnabled(True)
			self.last_button.setEnabled(True)
		if self.activeMsgIdx <= 0:
			self.prev_button.setEnabled(False)
			self.first_button.setEnabled(False)
		else:
			self.prev_button.setEnabled(True)
			self.first_button.setEnabled(True)
		self.message_indexEdit.setText(str(self.activeMsgIdx))
		self.update_msg_info()
		
	def last_msg(self):
		self.activeMsgIdx = self.num_msgs-1
		self.next_button.setEnabled(False)
		self.last_button.setEnabled(False)
		if self.activeMsgIdx <= 0:
			self.prev_button.setEnabled(False)
			self.first_button.setEnabled(False)
		else:
			self.prev_button.setEnabled(True)	
			self.first_button.setEnabled(True)
		self.message_indexEdit.setText(str(self.activeMsgIdx))
		self.update_msg_info()
		
	def update_msg_info(self):
		if self.activeMsgIdx > -1:
			self.c.execute("select fcount, payload, topic, gatewayMetaDataList0_rxInfo_time, gatewayMetaDataList0_name, gatewayMetaDataList0_mac, gatewayMetaDataList0_latitude, gatewayMetaDataList0_longitude from sensor_msg where deviceMetaData_deviceEUI = '" + self.sensors[self.activeSensorIdx][0] + "' and msg_id = '" + str(self.valid_msg_ids[self.activeMsgIdx]) + "'" + self.search_filters)
			results = self.c.fetchone()
			self.message_idEdit.setText(str(self.valid_msg_ids[self.activeMsgIdx]))
			self.message_idEdit.setCursorPosition(0)
		else:
			results = 8*[None]
			self.message_idEdit.clear()
		#
		if results[0] != 'None' and results[0] is not None:
			self.message_fcountEdit.setText(str(results[0]))
			self.message_fcountEdit.setCursorPosition(0)
		else:
			self.message_fcountEdit.clear()
		#
		if results[1] != 'None' and results[1] is not None:
			self.message_payloadEdit.setText(results[1])
			self.message_payloadEdit.setCursorPosition(0)
		else:
			self.message_payloadEdit.clear()
		#
		if results[2] != 'None' and results[2] is not None:
			self.message_topicEdit.setText(results[2])
			self.message_topicEdit.setCursorPosition(0)
		else:
			self.message_topicEdit.clear()
		#
		if results[3] != 'None' and results[3] is not None:
			self.message_timeEdit.setText(results[3])
			self.message_timeEdit.setCursorPosition(0)
		else:
			self.message_timeEdit.clear()
		#
		if results[4] != 'None' and results[4] is not None:
			self.message_gateway_nameEdit.setText(results[4])
			self.message_gateway_nameEdit.setCursorPosition(0)
		else:
			self.message_gateway_nameEdit.clear()
		#
		if results[5] != 'None' and results[5] is not None:
			self.message_gateway_macEdit.setText(results[5])
			self.message_gateway_macEdit.setCursorPosition(0)
		else:
			self.message_gateway_macEdit.clear()
		#
		if results[6] != 'None' and results[6] is not None and results[7] != 'None' and results[7] is not None:
			self.message_gateway_locEdit.setText(results[6] + "," + results[7])
			self.message_gateway_locEdit.setCursorPosition(0)
		else:
			self.message_gateway_locEdit.clear()
	
	def update_sensor_info(self):
		self.sensor_devEui_comboBox.setCurrentIndex(self.activeSensorIdx) 
		#
		if self.sensors[self.activeSensorIdx][2] != 'None' and self.sensors[self.activeSensorIdx][2] is not None:
			self.sensor_nameEdit.setText(self.sensors[self.activeSensorIdx][2])
		else:
			self.sensor_nameEdit.clear()
		self.sensor_nameEdit.setCursorPosition(0)
		#
		if self.sensors[self.activeSensorIdx][1] != 'None' and self.sensors[self.activeSensorIdx][1] is not None:
			self.sensor_appEuiEdit.setText(self.sensors[self.activeSensorIdx][1])
		else:
			self.sensor_appEuiEdit.clear()
		self.sensor_appEuiEdit.setCursorPosition(0)
		#
		if self.activeSensorHasLoc:
			self.sensor_locationEdit.setText(str(self.sensors[self.activeSensorIdx][3]) + "," + str(self.sensors[self.activeSensorIdx][4]))
			self.goto_loc_button.setEnabled(True)
		else:
			self.sensor_locationEdit.clear()
			self.sensor_locationEdit.clearFocus()
			self.sensor_locationEdit.setPlaceholderText("lat,lng")
			self.goto_loc_button.setEnabled(False)
		self.sensor_locationEdit.setCursorPosition(0)
	
	def update_sensor_location(self):		
		loc_str = str(self.sensor_locationEdit.text())
		if loc_str == 'None':
			self.c.execute("update sensors set lat = 'None' where devEUI = '" + self.sensors[self.activeSensorIdx][0] + "'")
			self.c.execute("update sensors set lng = 'None' where devEUI = '" + self.sensors[self.activeSensorIdx][0] + "'")
			self.conn.commit()
			self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("removeMarker('" + self.sensors[self.activeSensorIdx][0] + "')"))
			self.c.execute("select * from sensors")
			self.sensors = self.c.fetchall()
			self.sensor_locationEdit.clear()
			self.sensor_locationEdit.clearFocus()
			self.sensor_locationEdit.setPlaceholderText("lat,lng")
			self.goto_loc_button.setEnabled(False)
		else:
			try:
				comma_idx = loc_str.index(',')
				lat = float(loc_str[0:comma_idx])
				lng = float(loc_str[comma_idx+1:])
				self.c.execute("update sensors set lat = " + str(lat) + " where devEUI = '" + self.sensors[self.activeSensorIdx][0] + "'")
				self.c.execute("update sensors set lng = " + str(lng) + " where devEUI = '" + self.sensors[self.activeSensorIdx][0] + "'")
				self.conn.commit()
				if self.activeSensorHasLoc:
					self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("setMarkerLocation(" + str(lat) + "," + str(lng) + ")"))
				else:
					self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("createMarker(" + str(lat) + "," + str(lng) + ",'" + self.sensors[self.activeSensorIdx][2] + "','" + self.sensors[self.activeSensorIdx][0] + "')"))
					self.activeSensorHasLoc = True
				self.c.execute("select * from sensors")
				self.sensors = self.c.fetchall()
				self.goto_loc_button.setEnabled(True)
			except ValueError:
				if self.activeSensorHasLoc:
					self.sensor_locationEdit.setText(str(self.sensors[self.activeSensorIdx][3]) + "," + str(self.sensors[self.activeSensorIdx][4]))
					self.goto_loc_button.setEnabled(True)
				else:
					self.sensor_locationEdit.clear()
					self.sensor_locationEdit.clearFocus()
					self.sensor_locationEdit.setPlaceholderText("lat,lng")
					self.goto_loc_button.setEnabled(False)
		
	
	def update_gui(self):
		self.c.execute("select max(msg_id) from sensor_msg where deviceMetaData_deviceEUI = '" + self.sensors[self.activeSensorIdx][0] + "'" + self.search_filters)
		result = self.c.fetchone()[0]
		if result != None and result > self.valid_msg_ids[-1]: # new message received
			self.c.execute("select msg_id from sensor_msg where deviceMetaData_deviceEUI = '" + str(self.sensors[self.activeSensorIdx][0]) + "'" + self.search_filters + " order by msg_id asc") 
			self.valid_msg_ids = [id[0] for id in self.c.fetchall()]
			self.num_msgs = len(self.valid_msg_ids)
			if not self.last_button.isEnabled():
				self.activeMsgIdx = self.num_msgs-1
				self.last_msg()
			self.plot(self.plotType.currentText())
			
		self.c.execute("select * from sensors")
		results = self.c.fetchall()
		for result in results:
			if result not in self.sensors:
				self.sensor_devEui_comboBox.addItem(result[0])
				if result[3] != 'None' and result[3] is not None and result[4] != 'None' and result[4] is not None:
					self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("createMarker(" + str(result[3]) + "," + str(result[4]) + ",'" + result[2] + "','" + result[0] + "')"))
		self.sensors = results		

	def goto_location(self):
		if self.activeSensorHasLoc:
			self.gmap_webView.page().mainFrame().evaluateJavaScript(QString("centerMap(" + str(self.sensors[self.activeSensorIdx][3]) + "," + str(self.sensors[self.activeSensorIdx][4]) + ")"))			
		
	def update_locks(self):
		self.search_filters = ''
		#
		if self.message_id_lock.locked:
			filt = "msg_id " + str(self.message_id_sqlEdit.displayText())
			try:
				self.c.execute("select msg_id from sensor_msg where " + filt)
				tmp = self.c.fetchone()
				self.search_filters += " and " + filt
				self.message_id_sqlEdit.setReadOnly(True)
				self.message_id_sqlEdit.setDisabled(True)
				self.message_id_sqlEdit.setStyleSheet("QLineEdit { color: black }");
			except sqlite3.OperationalError:
				self.message_id_sqlEdit.setReadOnly(False)
				self.message_id_sqlEdit.setDisabled(False)
				self.message_id_sqlEdit.setStyleSheet("QLineEdit { color: red }");
				return False
		else:
			self.message_id_sqlEdit.setReadOnly(False)
			self.message_id_sqlEdit.setDisabled(False)
			self.message_id_sqlEdit.setStyleSheet("QLineEdit { color: black }");
		#
		if self.message_fcount_lock.locked:
			filt = "fcount " + str(self.message_fcount_sqlEdit.displayText())
			try:
				self.c.execute("select msg_id from sensor_msg where " + filt)
				tmp = self.c.fetchone()
				self.search_filters += " and " + filt
				self.message_fcount_sqlEdit.setReadOnly(True)
				self.message_fcount_sqlEdit.setDisabled(True)
				self.message_fcount_sqlEdit.setStyleSheet("QLineEdit { color: black }");
			except sqlite3.OperationalError:
				self.message_fcount_sqlEdit.setReadOnly(False)
				self.message_fcount_sqlEdit.setDisabled(False)
				self.message_fcount_sqlEdit.setStyleSheet("QLineEdit { color: red }");
				return False
		else:
			self.message_fcount_sqlEdit.setReadOnly(False)
			self.message_fcount_sqlEdit.setDisabled(False)
			self.message_fcount_sqlEdit.setStyleSheet("QLineEdit { color: black }");
		#
		if self.message_payload_lock.locked:
			filt = "payload " + str(self.message_payload_sqlEdit.displayText())
			try:
				self.c.execute("select msg_id from sensor_msg where " + filt)
				tmp = self.c.fetchone()
				self.search_filters += " and " + filt
				self.message_payload_sqlEdit.setReadOnly(True)
				self.message_payload_sqlEdit.setDisabled(True)
				self.message_payload_sqlEdit.setStyleSheet("QLineEdit { color: black }");
			except sqlite3.OperationalError:
				self.message_payload_sqlEdit.setReadOnly(False)
				self.message_payload_sqlEdit.setDisabled(False)
				self.message_payload_sqlEdit.setStyleSheet("QLineEdit { color: red }");
				return False
		else:
			self.message_payload_sqlEdit.setReadOnly(False)
			self.message_payload_sqlEdit.setDisabled(False)
			self.message_payload_sqlEdit.setStyleSheet("QLineEdit { color: black }");
		#
		if self.message_topic_lock.locked:
			filt = "topic " + str(self.message_topic_sqlEdit.displayText())
			try:
				self.c.execute("select msg_id from sensor_msg where " + filt)
				tmp = self.c.fetchone()
				self.search_filters += " and " + filt
				self.message_topic_sqlEdit.setReadOnly(True)
				self.message_topic_sqlEdit.setDisabled(True)
				self.message_topic_sqlEdit.setStyleSheet("QLineEdit { color: black }");
			except sqlite3.OperationalError:
				self.message_topic_sqlEdit.setReadOnly(False)
				self.message_topic_sqlEdit.setDisabled(False)
				self.message_topic_sqlEdit.setStyleSheet("QLineEdit { color: red }");
				return False
		else:
			self.message_topic_sqlEdit.setReadOnly(False)
			self.message_topic_sqlEdit.setDisabled(False)
			self.message_topic_sqlEdit.setStyleSheet("QLineEdit { color: black }");
		#
		if self.message_time_lock.locked:
			filt = "gatewayMetaDataList0_rxInfo_time " + str(self.message_time_sqlEdit.displayText())
			try:
				self.c.execute("select msg_id from sensor_msg where " + filt)
				tmp = self.c.fetchone()
				self.search_filters += " and " + filt
				self.message_time_sqlEdit.setReadOnly(True)
				self.message_time_sqlEdit.setDisabled(True)
				self.message_time_sqlEdit.setStyleSheet("QLineEdit { color: black }");
			except sqlite3.OperationalError:
				self.message_time_sqlEdit.setReadOnly(False)
				self.message_time_sqlEdit.setDisabled(False)
				self.message_time_sqlEdit.setStyleSheet("QLineEdit { color: red }");
				return False
		else:
			self.message_time_sqlEdit.setReadOnly(False)
			self.message_time_sqlEdit.setDisabled(False)
			self.message_time_sqlEdit.setStyleSheet("QLineEdit { color: black }");
		#
		if self.message_gateway_name_lock.locked:
			filt = "gatewayMetaDataList0_name " + str(self.message_gateway_name_sqlEdit.displayText())
			try:
				self.c.execute("select msg_id from sensor_msg where " + filt)
				tmp = self.c.fetchone()
				self.search_filters += " and " + filt
				self.message_gateway_name_sqlEdit.setReadOnly(True)
				self.message_gateway_name_sqlEdit.setDisabled(True)
				self.message_gateway_name_sqlEdit.setStyleSheet("QLineEdit { color: black }");
			except sqlite3.OperationalError:
				self.message_gateway_name_sqlEdit.setReadOnly(False)
				self.message_gateway_name_sqlEdit.setDisabled(False)
				self.message_gateway_name_sqlEdit.setStyleSheet("QLineEdit { color: red }");
				return False
		else:
			self.message_gateway_name_sqlEdit.setReadOnly(False)
			self.message_gateway_name_sqlEdit.setDisabled(False)
			self.message_gateway_name_sqlEdit.setStyleSheet("QLineEdit { color: black }");
		#
		if self.message_gateway_mac_lock.locked:
			filt = "gatewayMetaDataList0_mac " + str(self.message_gateway_mac_sqlEdit.displayText())
			try:
				self.c.execute("select msg_id from sensor_msg where " + filt)
				tmp = self.c.fetchone()
				self.search_filters += " and " + filt
				self.message_gateway_mac_sqlEdit.setReadOnly(True)
				self.message_gateway_mac_sqlEdit.setDisabled(True)
				self.message_gateway_mac_sqlEdit.setStyleSheet("QLineEdit { color: black }");
			except sqlite3.OperationalError:
				self.message_gateway_mac_sqlEdit.setReadOnly(False)
				self.message_gateway_mac_sqlEdit.setDisabled(False)
				self.message_gateway_mac_sqlEdit.setStyleSheet("QLineEdit { color: red }");
				return False
		else:
			self.message_gateway_mac_sqlEdit.setReadOnly(False)
			self.message_gateway_mac_sqlEdit.setDisabled(False)
			self.message_gateway_mac_sqlEdit.setStyleSheet("QLineEdit { color: black }");
		#	
		if self.message_gateway_loc_lock.locked:
			
			try:
				loc_str = str(self.message_gateway_loc_sqlEdit.displayText())
				comma_idx = loc_str.index(',')
				lat = float(loc_str[0:comma_idx])
				lng = float(loc_str[comma_idx+1:])
				filt = "gatewayMetaDataList0_latitude = '" + str(lat) + "' and gatewayMetaDataList0_longitude = '" + str(lng) + "'"
			
				self.c.execute("select msg_id from sensor_msg where " + filt)
				tmp = self.c.fetchone()
				self.search_filters += " and " + filt
				self.message_gateway_loc_sqlEdit.setReadOnly(True)
				self.message_gateway_loc_sqlEdit.setDisabled(True)
				self.message_gateway_loc_sqlEdit.setStyleSheet("QLineEdit { color: black }");
			except:
				self.message_gateway_loc_sqlEdit.setReadOnly(False)
				self.message_gateway_loc_sqlEdit.setDisabled(False)
				self.message_gateway_loc_sqlEdit.setStyleSheet("QLineEdit { color: red }");
				return False
		else:
			self.message_gateway_loc_sqlEdit.setReadOnly(False)
			self.message_gateway_loc_sqlEdit.setDisabled(False)
			self.message_gateway_loc_sqlEdit.setStyleSheet("QLineEdit { color: black }");
		#
		self.c.execute("select msg_id from sensor_msg where deviceMetaData_deviceEUI = '" + str(self.sensors[self.activeSensorIdx][0]) + "'" + self.search_filters + " order by msg_id asc")
		self.valid_msg_ids = [i[0] for i in self.c.fetchall()]
		self.num_msgs = len(self.valid_msg_ids)
		self.activeMsgIdx = self.num_msgs-1
		self.last_msg()
		self.plot(str(self.plotType.currentText()))
		return True
		
	def update_msg_idx(self):
		msg_idx = str(self.message_indexEdit.text())
		try:
			msg_idx = int(msg_idx)
			if msg_idx >= 0 and msg_idx <= self.num_msgs-1:
				self.activeMsgIdx = msg_idx
				if self.activeMsgIdx >= self.num_msgs-1:
					self.next_button.setEnabled(False)
					self.last_button.setEnabled(False)
				else:
					self.next_button.setEnabled(True)
					self.last_button.setEnabled(True)
				if self.activeMsgIdx <= 0:
					self.prev_button.setEnabled(False)
					self.first_button.setEnabled(False)
				else:
					self.prev_button.setEnabled(True)	
					self.first_button.setEnabled(True)		
				self.update_msg_info()
			else:
				self.message_indexEdit.setText(str(self.activeMsgIdx))
		except ValueError:
			self.message_indexEdit.setText(str(self.activeMsgIdx))
	
	@pyqtSlot()
	def restore_if_empty(self):
		if self.sender().displayText() == '':
			self.update_msg_info()
		
	def enableWidgets(self,enable):
		self.sensor_devEui_comboBox.clear()
		self.sensor_devEui_comboBox.setEnabled(enable)
		#
		self.sensor_nameEdit.clear()
		self.sensor_nameEdit.setDisabled(not enable)
		#
		self.sensor_appEuiEdit.clear()
		self.sensor_appEuiEdit.setDisabled(not enable)
		#
		self.sensor_locationEdit.clear()
		self.sensor_locationEdit.setDisabled(not enable)
		self.sensor_locationEdit.setReadOnly(not enable)
		#
		self.message_idEdit.clear()
		self.message_idEdit.setDisabled(not enable)
		self.message_id_sqlEdit.clear()
		self.message_id_sqlEdit.setReadOnly(not enable)
		self.message_id_sqlEdit.setDisabled(not enable)
		self.message_id_lock.setEnabled(enable)
		#
		self.message_fcountEdit.clear()
		self.message_fcountEdit.setDisabled(not enable)
		self.message_fcount_sqlEdit.clear()
		self.message_fcount_sqlEdit.setReadOnly(not enable)
		self.message_fcount_sqlEdit.setDisabled(not enable)
		self.message_fcount_lock.setEnabled(enable)
		#
		self.message_payloadEdit.clear()
		self.message_payloadEdit.setDisabled(not enable)
		self.message_payload_sqlEdit.clear()
		self.message_payload_sqlEdit.setReadOnly(not enable)
		self.message_payload_sqlEdit.setDisabled(not enable)
		self.message_payload_lock.setEnabled(enable)
		#
		self.message_topicEdit.clear()
		self.message_topicEdit.setDisabled(not enable)
		self.message_topic_sqlEdit.clear()
		self.message_topic_sqlEdit.setReadOnly(not enable)
		self.message_topic_sqlEdit.setDisabled(not enable)
		self.message_topic_lock.setEnabled(enable)
		#
		self.message_timeEdit.clear()
		self.message_timeEdit.setDisabled(not enable)
		self.message_time_sqlEdit.clear()
		self.message_time_sqlEdit.setReadOnly(not enable)
		self.message_time_sqlEdit.setDisabled(not enable)
		self.message_time_lock.setEnabled(enable)
		#
		self.message_gateway_nameEdit.clear()
		self.message_gateway_nameEdit.setDisabled(not enable)
		self.message_gateway_name_sqlEdit.clear()
		self.message_gateway_name_sqlEdit.setReadOnly(not enable)
		self.message_gateway_name_sqlEdit.setDisabled(not enable)
		self.message_gateway_name_lock.setEnabled(enable)
		#
		self.message_gateway_macEdit.clear()
		self.message_gateway_macEdit.setDisabled(not enable)
		self.message_gateway_mac_sqlEdit.clear()
		self.message_gateway_mac_sqlEdit.setReadOnly(not enable)
		self.message_gateway_mac_sqlEdit.setDisabled(not enable)
		self.message_gateway_mac_lock.setEnabled(enable)
		#
		self.message_gateway_locEdit.clear()
		self.message_gateway_locEdit.setDisabled(not enable)
		self.message_gateway_loc_sqlEdit.clear()
		self.message_gateway_loc_sqlEdit.setReadOnly(not enable)
		self.message_gateway_loc_sqlEdit.setDisabled(not enable)
		self.message_gateway_loc_lock.setEnabled(enable)
		#
		self.message_indexEdit.clear()
		self.message_indexEdit.setDisabled(not enable)
		self.message_indexEdit.setReadOnly(not enable)
		#
		self.first_button.setEnabled(enable)
		self.prev_button.setEnabled(enable)
		self.next_button.setEnabled(enable)
		self.last_button.setEnabled(enable)
		#
		self.plotType.setEnabled(enable)
		
if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = Window()
	window.show()
	app.exec_()