import requests

url = 'https://storage.googleapis.com/epschedule-avatars/aec56023295543512d5395bf73e41d44cb5f8c99b38da0f4d4a1647879d3944a.jpg'
response = requests.get(url)
if response.status_code == 200:
    with open('cloud_cwest_icon.jpg', 'wb') as f:
        f.write(response.content)
    print('Downloaded cloud image as cloud_cwest_icon.jpg')
else:
    print(f'Failed to download: {response.status_code}')