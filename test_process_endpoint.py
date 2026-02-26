import requests

def test_process():
    url = "http://localhost:8001/leads/process"
    payload = {
        "url": "https://example.com",
        "my_offer": "Web Scraping Services"
    }
    
    print(f"📡 Sending POST to {url}...")
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print("❌ Error Details:")
            print(response.text)
        else:
            print("✅ Success:")
            print(response.json())
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_process()
