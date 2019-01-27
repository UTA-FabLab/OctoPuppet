from __future__ import print_function
import json
import sys
import requests
from octoprint.server.api import api 
#app = Flask(__name__)

@api.route('/manualmode.py', methods=['GET']) 
def main():
	serverURL1= "DEV_URL/materials.php"
	serverURL2= "DEV_URL/purpose.php"
	headers = {'authorization': "FLUD_KEY"}
	response=""

#serverURL= sys.args[0]

#CHECKING THE STATUS FOR CONNECTION TO THE SERVER
	def check_status(serverURL):

	#print(serverURL)
		try:

			payload={"type": "device_id", "device":"DEV_ID"}
			r = requests.request("POST", serverURL, json=payload, headers=headers)
			response = r.json()
			r.raise_for_status()
			#print(response)
			if(serverURL=="DEV_URL/materials.php"):
				writetoMaterialsFile(response)
				#print("A backkup for materials data is ready!")
			elif(serverURL=="DEV_URL/purpose.php"):
				writetoPurposeFile(response)
				#print("A backkup for purpose data is ready!")

		except Exception:
			print(Exception)
			response = "Check Status: Unable to connect. Verify connection."
			#print(response)
			return response
		

		if(response=="Check Status: Unable to connect. Verify connection."):
			with open('/home/vrushali/.octoprint/FabAppData/materials.json','r') as m_data:
				
				materialsData = json.load(m_data)
				print("MATERIALS",m_data)
			#print(materialsData)
			with open('/home/vrushali/.octoprint/FabAppData/materials.json','r') as p_data:
				print("PURPOSE",p_data)
				purposeData = json.load(p_data)
			#print(purposeData)

		return response
		



#STORING THE DATA FOR MATERIALS AND PURPOSE IN JSON FILES
	def writetoMaterialsFile(response):
		data = json.dumps(response)
		open("/home/vrushali/.octoprint/FabAppData/materials.json","w").write(data)


	def writetoPurposeFile(response):
		data = json.dumps(response)
		open("/home/vrushali/.octoprint/FabAppData/purpose.json","w").write(data)
	
	response1= check_status(serverURL1)
	response2= check_status(serverURL2)


	#print("Response in main", response1)
	
	return response1
	#return response2




#if __name__ == '__main__':

	#main()
	#main()
	#print("Returned data ",data)
	#print("data after calling main method", data)
	#return data
	#return response
	#print("This is the response in the main",response)
#    app.run()
#    app.debug= True
    #main()
    #print("with main method")



