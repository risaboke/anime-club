import os
import pymysql
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template

load_dotenv()

app = Flask(__name__)

KITSU_URL = "https://kitsu.app/api/edge/anime"
VALID_STATUSES = ["want to watch", "watching", "finished"]

def get_connection():
    """Opens a connection to the MySQL database"""
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
    )

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

def get_rating(anime):
    """Returns the rating for sorting. A missing rating counts as 0"""
    if anime ["rating"] is None:
        return 0
    return anime["rating"]

def get_episodes(anime):
    """This returns the episode count for sorting. A missing count counts as 0"""
    if anime["episodes"] is None:
        return 0
    return anime["episodes"]

def get_title(anime):
    """This returns the lowercase title so A-Z sorting ignores capital letters"""
    return anime["title"].lower()

def filter_results(results, genre, status):
    """Keep the anime that only matches the chosen genre and status"""
    filtered = []
    for anime in results:
        if genre != "":
            lowercase_genres = []
            for g in anime["genres"]:
                lowercase_genres.append(g.lower())
            if genre.lower() not in lowercase_genres:
                continue

        if status != "" and anime["status"] != status:
            continue
        filtered.append(anime)
    return filtered

def sort_results(results, sort_by):
    """Returns the list sorted by the chosen option"""
    if sort_by == "rating":
        return sorted(results, key=get_rating, reverse=True)
    if sort_by == "episodes":
        return sorted(results, key=get_episodes, reverse=True)
    if sort_by == "title":
        return sorted(results, key=get_title)
    return results

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/search")
def search ():
    title = request.args.get("q", "").strip()
    genre = request.args.get("genre", "").strip()
    status = request.args.get("status", "").strip().lower()
    sort_by = request.args.get("sort", "").strip().lower()

    if title == "":
        return jsonify({"error": "Type an anime title"}), 400
    if sort_by not in ["", "rating", "episodes", "title"]:
        return jsonify ({"error": "sort must be rating, episodes, or title"}), 400
    try:
        results = search_anime(title)
    except requests.exceptions.RequestException:
        return jsonify({"error": "Could not reach Kitsu. Please try again later."}), 503

    results = filter_results(results, genre, status)
    results = sort_results(results, sort_by)

    return jsonify(results)

@app.route("/api/shelf", methods=["POST"])
def add_to_shelf():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Send the data as JSON"}), 400

    member_name = str(data.get("member_name") or "").strip()
    anime_id = str(data.get("anime_id") or "").strip()
    title = str(data.get("title") or "").strip()
    poster = data.get("poster")
    status = str(data.get("status") or "").strip().lower()
    rating = data.get("rating")
    opinion = str(data.get("opinion") or "").strip()

    if member_name == "" or len(member_name) > 50:
        return jsonify({"error": "Please enter your name (50 characters or fewer)"}), 400
    if anime_id == "" or title == "":
        return jsonify({"error": "Missing anime information"}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": "Status must be 'want to watch', 'watching', or 'finished'"}), 400
    if rating is not None:
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be a whole number from 1 to 5"}), 400
        if len(opinion) > 1000:
            return jsonify({"error", "Opinion must be 1000 characters or fewer"}), 400
        
        try:
            connection = get_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM shelf WHERE member_name = %s AND anime_id = %s",
                        (member_name, anime_id),
                    )
                    existing = cursor.fetchone()

                    if existing:
                        cursor.execute(
                            "UPDATE shelf SET status = %s, rating = %s, opinion = %s WHERE id = %s",
                            (status, rating, opinion, existing["id"]),
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO shelf (member_name, anime_id, title, poster, status, rating, opinion) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (member_name, anime_id, title, poster, status, rating, opinion),
                        )
                connection.commit()
            finally:
                connection.close()
        except pymysql.MySQLError as error:
            print("Databse error:", error)
            return jsonify({"error": "Could not reach the database. Please try again later"}), 503

        return jsonify({"message": "Saved to your shelf"}), 201

@app.route("/api/shelf")
def get_shelf():
    member_name = request.args.get("member", "").strip()
    if member_name == "":
        return jsonify({"error": "Plese enter your name"}), 400

    try:
        connection = get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT anime_id, title, poster, status, rating, opinion "
                    "FROM shelf WHERE member_name = %s ORDER BY created_at DESC",
                    (member_name,),
                )
                rows = cursor.fetchall()
        finally:
            connection.close()
    except pymysql.MySQLError as error:
        print("Database error:", error)
        return jsonify({"error": "Could not reach the database. Please try again later"}), 503

    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True)
