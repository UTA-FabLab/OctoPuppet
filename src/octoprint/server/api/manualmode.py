from __future__ import print_function
import json
import sys
import requests

serverURL1= "FLUD_BASE/materials.php"
serverURL2= "FLUD_BASE/purpose.php"
headers = {'authorization': "FLUD_KEY"}
response=""

#CHECKING THE STATUS FOR CONNECTION TO THE SERVER
def check_status(serverURL):
	#print(serverURL)
	try:
		payload={"type": "device_id", "device":"DEV_ID"}
		r = requests.request("POST", serverURL, json=payload, headers=headers)
		response = r.json()
		r.raise_for_status()
		print(response)
		if(serverURL=="FLUD_BASE/materials.php"):
			writetoMaterialsFile(response)
			print("A backkup for materials data is ready!")
		elif(serverURL=="FLUD_BASE/purpose.php"):
			writetoPurposeFile(response)
			print("A backkup for purpose data is ready!")

	except Exception:
		print(Exception)
		response = "Check Status: Unable to connect. Verify connection."
		print(response)
		return response
		

		if(response=="Check Status: Unable to connect. Verify connection."):
			with open('/home/vrushali/.octoprint/uploads/materials.json','r') as m_data:
				
				materialsData = json.load(m_data)
				print("MATERIALS",m_data)
			print(materialsData)
			with open('/home/vrushali/.octoprint/uploads/purpose.json','r') as p_data:
				print("PURPOSE",p_data)
				purposeData = json.load(p_data)
			print(purposeData)
		



#STORING THE DATA FOR MATERIALS AND PURPOSE IN JSON FILES
def writetoMaterialsFile(response):
	data = json.dumps(response)
	open("/home/vrushali/.octoprint/FabAppData/materials.json","w").write(data)


def writetoPurposeFile(response):
	data = json.dumps(response)
	open("/home/vrushali/.octoprint/FabAppData/purpose.json","w").write(data)


check_status(serverURL1)
check_status(serverURL2)
