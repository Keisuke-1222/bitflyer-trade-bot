import requests

def notify(message):
    url = "https://notify-api.line.me/api/notify"
    token = "YOUR_TOKEN"
    headers = {"Authorization": "Bearer " + token}

    payload = {"message": message}

    r = requests.post(url, headers=headers, params=payload)
