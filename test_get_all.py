import requests
import json

def test_get_leads():
    try:
        url = "http://localhost:8001/leads/"
        print(f"📡 GET {url} ...")
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"Received {len(data)} leads.")
            if len(data) > 0:
                print("First lead sample:")
                print(json.dumps(data[0], indent=2))
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"Crash: {e}")

if __name__ == "__main__":
    test_get_leads()
