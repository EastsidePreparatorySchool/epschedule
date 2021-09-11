import csv
import json

def make_json(csvFilePath, jsonFilePath):
	data = []

	with open(csvFilePath, encoding='utf=8') as csvf:
		csvReader = csv.DictReader(csvf)

		for row in csvReader:
			data.append(row['login'])

	with open(jsonFilePath, 'w', encoding='utf-8') as jsonf:
		jsonf.write(json.dumps(data, indent=4))


csvFilePath = 'four11_map.csv'
jsonFilePath = 'four11_map.json'

make_json(csvFilePath, jsonFilePath)