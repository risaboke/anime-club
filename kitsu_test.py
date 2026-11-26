import requests

url = "https://kitsu.app/api/edge/anime"
response = requests.get(url, params={"filter[text]": "frieren", "page[limit]": 3})

print(response.status_code)

data = response.json()
for item in data["data"]:
    attributes = item["attributes"]
    print(attributes["canonicalTitle"])
    print(attributes["averageRating"])