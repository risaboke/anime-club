import requests

BASE = "http://127.0.0.1:5000"

entry = {
    "member_name": "tester",
    "anime_id": "46474",
    "title": "Sousou no Frieren",
    "poster": None,
    "status": "finished",
    "rating": 5,
    "opinion": "Test opinion",
}

response = requests.post(BASE + "/api/shelf", json=entry)
print(response.status_code, response.text[:300])

response = requests.get(BASE + "/api/shelf", params={"member": "tester"})
print(response.status_code, response.text[:300])