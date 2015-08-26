import json
import os

readfile = open('../schedules.json', 'rb')
schedules = json.load(readfile)
coords = [
{'name':'MS', 'latitude':47.643288, 'longitude':-122.198141},
{'name':'OH', 'latitude':47.643419, 'longitude':-122.199274},
{'name':'FG', 'latitude':47.643227, 'longitude':-122.198397},
{'name':'AS', 'latitude':47.643628, 'longitude':-122.199320},
{'name':'HB', 'latitude':47.643717, 'longitude':-122.198997},
{'name':'LPC', 'latitude':47.643455, 'longitude':-122.198769},
{'name':'FLC', 'latitude':47.643834, 'longitude':-122.199138},
{'name':'TMAC', 'latitude':47.643336, 'longitude':-122.199038},
]

rooms = []
for schedule in schedules:
	for classObj in schedule['classes']:
		inRooms = False;
		for room in rooms:
			if room['name'] == classObj['room']:
				inRooms = True;
				break;
		if not inRooms:
			for building in coords:
				if(classObj['room'][0:len(building['name'])] == building['name']):
					rooms.append({'name':classObj['room'].lower(), 'latitude':building['latitude'], 'longitude':building['longitude']})
					break

writefile = open('../room_locations.json', 'wb')
writefile.write(json.dumps(rooms))