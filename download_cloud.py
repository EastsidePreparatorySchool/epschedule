import requests

url = "https://epschedule-avatars.storage.googleapis.com/ee8aa33ffbbf2f24b23d38b5c19a21246b2dae0a6b22592335a311c5f48dc00d.jpg"
response = requests.get(url)
if response.status_code == 200:
    with open("cloud_ajosan_icon.jpg", "wb") as f:
        f.write(response.content)
    print("Downloaded cloud image as cloud_ajosan_icon.jpg")
else:
    print(f"Failed to download: {response.status_code}")
