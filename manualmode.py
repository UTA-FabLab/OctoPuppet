from __future__ import print_function
import json
import sys
import requests

serverURL1= "https://afabapp-dev.uta.edu/api/materials.php"
serverURL2= "https://afabapp-dev.uta.edu/api/purpose.php"
headers = {'authorization': "HDVmyqkZB5vsPQGAKwpLtPPQ8Pauy5DMVWsefcBVsbzv9AQnrJFhyAuqBhLCL9r8AFxtDAgjc7Qjf8bdL9eaAXd7VnejU7DHw"}
response=""

#CHECKING THE STATUS FOR CONNECTION TO THE SERVER
def check_status(serverURL):
	#print(serverURL)
	try:
		payload={"type": "device_id", "device":"0026"}
		r = requests.request("POST", serverURL, json=payload, headers=headers)
		response = r.json()
		r.raise_for_status()
		print(response)
		if(serverURL=="https://fabapp-dev.uta.edu/api/materials.php"):
			writetoMaterialsFile(response)
			print("A backkup for materials data is ready!")
		elif(serverURL=="https://fabapp-dev.uta.edu/api/purpose.php"):
			writetoPurposeFile(response)

	except Exception:
		print(Exception)
		response = "Check Status: Unable to connect. Verify connection."
		print(response)
		return response

		if(response=="Check Status: Unable to connect. Verify connection."):
			with open('/home/vrushali/.octoprint/uploads/materials.json','r') as m_data:
				#print(m_data)
				materialsData = json.load(m_data)
			print(materialsData)
			with open('/home/vrushali/.octoprint/uploads/purpose.json','r') as p_data:
				#print(p_data)
				purposeData = json.load(p_data)
			print(purposeData)



#STORING THE DATA FOR MATERIALS AND PURPOSE IN JSON FILES
def writetoMaterialsFile(response):
	data = json.dumps(response)
	open("/home/vrushali/.octoprint/uploads/materials.json","w").write(data)


def writetoPurposeFile(response):
	data = json.dumps(response)
	open("/home/vrushali/.octoprint/uploads/purpose.json","w").write(data)

check_status(serverURL1)
check_status(serverURL2)






