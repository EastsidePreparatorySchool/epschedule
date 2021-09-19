import csv
import json

CSV_FILE_PATH = "four11_map.csv"
JSON_FILE_PATH = "four11_map.json"


def make_json(csv_file_path, json_file_path):
    data = []

    with open(csv_file_path, encoding="utf=8") as csvf:
        csv_reader = csv.DictReader(csvf)

    for row in csv_reader:
        data.append(row["login"])

    with open(json_file_path, "w", encoding="utf-8") as jsonf:
        jsonf.write(json.dumps(data, indent=4))


make_json(CSV_FILE_PATH, JSON_FILE_PATH)
