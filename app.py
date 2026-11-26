import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

KITSU_URL = "https://kitsu.app/api/edge/anime"

def get_site_name(url):
    """Turns a streaming link into a simple site name"""
    if "crunchyroll" in url:
        return "Crunchyroll"
    if "netflix" in url:
        return "Netflix"
    if "youtu" in url:
        return "YouTube"
    return "Other site"

def search_anime(title):
    """Asks Kitsu for anime matching the title and return a simple list"""
    response = requests.get(
        KITSU_URL, params={"filter[text]": title, "page[limit]": 10, "include": "categories,streamingLinks", }, timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    #store the extra info in dictionaries to find it by id
    categories_by_id = {}
    links_by_id = {}
    for extra in data.get("included", []):
        if extra["type"] == "categories":
            categories_by_id[extra["id"]] = extra["attributes"]["title"]
        elif extra["type"] == "streamingLinks":
            links_by_id[extra["id"]] = extra["attributes"]
    #build the clean list, one anime at a time
    results = []
    for item in data["data"]:
        attributes = item["attributes"]

        if attributes["nsfw"]:
            continue

        rating = attributes["averageRating"]
        if rating is not None:
            rating = round(float(rating) / 20, 1)

        poster = None
        if attributes["posterImage"]:
            poster = attributes["posterImage"]["medium"]

        genres = []
        category_refs = item["relationships"]["categories"].get("data", [])
        for ref in category_refs:
            name = categories_by_id.get(ref["id"])
            if name:
                genres.append(name)

        watch_links = []
        link_refs = item["relationships"]["streamingLinks"].get("data", [])
        for ref in link_refs:
            link = links_by_id.get(ref["id"])
            if link:
                watch_links.append({
                    "site": get_site_name(link["url"]),
                    "url": link["url"],
                    "subs": link.get("subs", []),
                    "dubs":link.get("dubs", [])
                })

        results.append({
            "id": item["id"],
            "title": attributes["canonicalTitle"],
            "rating": rating,
            "episodes": attributes["episodeCount"],
            "status": attributes["status"],
            "poster": poster,
            "genres": genres,
            "watch_links": watch_links,
        })

    return results

@app.route("/")
def home():
    return "Anime Club is running"

@app.route("/api/search")
def search ():
    title = request.args.get("q", "").strip()

    if title == "":
        return jsonify({"error": "Type an anime title"}), 400
    try:
        results = search_anime(title)
    except requests.exceptions.RequestException:
        return jsonify({"error": "Could not reach Kitsu. Please try again later."}), 503
    
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
