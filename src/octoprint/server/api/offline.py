# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Tushar Saini - UTA FabLab"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import requests, requests.exceptions

try:
	from os import scandir
except ImportError:
	from scandir import scandir

import json
import time
from flask import jsonify, request, url_for

from octoprint.settings import settings
from octoprint.server.api import api
from octoprint.server import printer
from octoprint.printer import standard

basedir = settings().getBaseFolder("FabAppData")
faUrl = settings().get(["fabapp", "faUrl"])
faDevice = {
	'device_id': str(settings().get(["fabapp", "faDev"]))
	}
faHeaders = {
	'authorization': settings().get(["fabapp", "faKey"])
	}

faPayload = faDevice.copy()

@api.route("/FabAppData", methods=["GET"])
def getLocalList():
	files = dict()
	for entry in scandir(basedir):
		identifier = entry.name[:-len(".json")]
		files[identifier] = url_for("index", _external=True) + "api/FabAppData/" + entry.name
	return jsonify(files)


@api.route("/FabAppData/status", methods=["GET"])
def FabAppStatus():
	try:
		r = requests.get(faUrl + "index.php", timeout=1)
		r.raise_for_status()
	except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError):
		return jsonify({"status": 500})
	else:
		return jsonify({"status": 200})

@api.route("/FabAppData/<string:filename>", methods=["GET", "POST"])
def tryFabAppOrGetLocal(filename):
	fname = os.path.join(basedir, filename + ".json")
	payload = request.get_json()
	faPayload['fa_status'] = "online"
	faPayload.update(payload)
	print(faPayload)
	try:
		r = requests.request("POST", faUrl + "api/" + filename + ".php", json=faPayload, headers=faHeaders, timeout=0.5)
		response = r.json()
		print("Connection to FabApp successful. Updating " + fname)
		if filename == "flud":
			pass
		else:
			open(fname, "w+").write(json.dumps(response, ensure_ascii=False))
	
		return jsonify(response)

	except:
		print("ALERT -- No connection to FabApp. Using local cache from " + fname)
		if filename == "flud":
			json_list=[]
			trans_id = "OFF"+str(int(time.time()))
			dummy_response = {"authorized":"Y", "status_id": 10, "trans_id": trans_id}
			faPayload['fa_status'] = "offline"
			faPayload['upload_status'] = 0
			faPayload['trans_id'] = trans_id
			if not os.path.isfile(fname):
				json_list.append(faPayload)
				with open(fname, mode='w') as f:
					f.write(json.dumps(json_list, sort_keys=True, indent=2))
			else:
				with open(fname) as oldjson:
					try:
						json_list = json.load(oldjson)
					except:
						json_list = []

				json_list.append(faPayload)
				with open(fname, mode='w') as f:
					f.write(json.dumps(json_list, sort_keys=True, indent=2))
			
			return jsonify(dummy_response)
		else:
			with open(fname, "r") as f:
				return jsonify(json.load(f))


@api.route("/FabAppData/sendOfflineData", methods=["GET", "POST"])
def sendOfflineData():
	trans_list=[]
	new_trans_list=[]
	fname = os.path.join(basedir, "flud.json")
	with open(fname) as f:
		trans_list = json.load(f)

	for transactions in trans_list:
		transactions['off_trans_id'] = transactions['trans_id']
		del transactions['trans_id']
		try:
			r = requests.request("POST", faUrl + "api/flud.php", json=transactions, headers=faHeaders)
			response = r.json()
			transactions['upload_status'] = response['off_status']
			currentData = printer.get_current_data()
			if currentData["state"]["text"] == "Printing":
				currentTrans = currentData["progress"]["transId"]
				if transactions['off_trans_id'] != currentTrans:
					standard.endtransaction()
				else:
					pass
			else:
				standard.endtransaction()

			print("Offline Transaction " + str(transactions['off_trans_id']) + " pushed")
		except Exception as e:
			print("Offline Transaction " + str(transactions['off_trans_id']) + " push failed: " + str(e))

		new_trans_list.append(transactions)
	
	with open(os.path.join(basedir, "status.json"), mode='w+') as f:
		f.write(json.dumps(new_trans_list, sort_keys=True, indent=2))

	return jsonify(new_trans_list)
