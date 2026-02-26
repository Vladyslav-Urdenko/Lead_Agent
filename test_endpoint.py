import requests
try:
    response = requests.post(
        "http://localhost:8001/leads/radar/maps",
        json={"query": "coffee shop", "location": "Seattle, WA", "max_results": 1},
        timeout=5
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
