import requests

base_url = 'http://localhost:8001'
url = f'{base_url}/transcribe/'
files = {'audio_file': open('data/test2.ogg', 'rb')}
response = requests.post(url=url, files=files)
print(response.status_code)
if response.status_code == 200:
    print(response.json())