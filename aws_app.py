from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import uuid
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = "palak_cinemaPulse_secret_key"

# ================= AWS CONFIG =================
REGION = "us-east-1"

SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:526562556656:CinemaPulse-Topic"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)

# DynamoDB Tables
users_table = dynamodb.Table("CinemaPulse-Users")
movies_table = dynamodb.Table("CinemaPulse-Movies")
feedbacks_table = dynamodb.Table("CinemaPulse-Feedbacks")
analytics_table = dynamodb.Table("CinemaPulse-Analytics")

# ================= SNS NOTIFICATION =================
def send_notification(subject, message):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
        print(f"[SNS SENT] {subject}")
    except ClientError as e:
        print("SNS Error:", e)

# ================= HELPERS =================
def is_logged_in():
    return "user_email" in session

def default_analytics_payload(movie_id=""):
    return {
        "movie_id": movie_id,
        "score": 0,
        "breakdown": {"positive": 0, "neutral": 0, "negative": 0},
        "trend": "Stable",
        "last_updated": None
    }

def get_feedbacks_for_movie(movie_id):
    res = feedbacks_table.scan()
    items = res.get("Items", [])
    return [f for f in items if f["movie_id"] == movie_id]

def get_feedbacks_for_user(user_email):
    res = feedbacks_table.scan()
    items = res.get("Items", [])
    return [f for f in items if f["user_email"] == user_email]

# ================= SIMPLE SENTIMENT =================
def simple_sentiment_analysis(comment):
    positive_words = ["amazing", "great", "excellent", "masterpiece", "good", "love"]
    negative_words = ["bad", "boring", "waste", "poor", "predictable"]

    text = comment.lower()
    score = 0

    for w in positive_words:
        if w in text:
            score += 1
    for w in negative_words:
        if w in text:
            score -= 1

    if score > 0:
        return "Positive"
    elif score < 0:
        return "Negative"
    return "Neutral"

# ================= MOVIE ANALYTICS LOGIC =================
def update_movie_analytics(movie_id):
    feedbacks = get_feedbacks_for_movie(movie_id)

    if not feedbacks:
        analytics_table.put_item(Item=default_analytics_payload(movie_id))
        return

    positive = sum(1 for f in feedbacks if f["sentiment"] == "Positive")
    neutral = sum(1 for f in feedbacks if f["sentiment"] == "Neutral")
    negative = sum(1 for f in feedbacks if f["sentiment"] == "Negative")
    total = len(feedbacks)

    score = int((positive * 100 + neutral * 50 + negative * 10) / total)

    if score > 75:
        trend = "Trending Up"
    elif score > 50:
        trend = "Stable"
    else:
        trend = "Trending Down"

    payload = {
        "movie_id": movie_id,
        "score": score,
        "breakdown": {
            "positive": int((positive / total) * 100),
            "neutral": int((neutral / total) * 100),
            "negative": int((negative / total) * 100)
        },
        "trend": trend,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    analytics_table.put_item(Item=payload)

# ================= MOVIE RATING LOGIC =================
def update_movie_rating(movie_id):
    feedbacks = get_feedbacks_for_movie(movie_id)

    if not feedbacks:
        new_rating = 0.0
    else:
        new_rating = round(sum(f["rating"] for f in feedbacks) / len(feedbacks), 1)

    movies_table.update_item(
        Key={"id": movie_id},
        UpdateExpression="SET rating = :r",
        ExpressionAttributeValues={":r": new_rating}
    )

# ==========================================================
# ================= RUN ONLY ONCE SECTION ==================
# ==========================================================
"""
UNCOMMENT THIS BLOCK ONLY FOR FIRST TIME DATABASE SEEDING.
AFTER RUNNING ONCE, COMMENT IT PERMANENTLY.

This section:
1. Seeds initial movies (Jawan, Oppenheimer)
2. Seeds initial feedbacks
3. Creates initial analytics entries

DO NOT RUN THIS AGAIN AFTER FIRST SUCCESSFUL EXECUTION.
"""

# Initial Movies
initial_movies = [
    {
        "id": str(uuid.uuid4()),
        "name": "Jawan",
        "genre": "Action",
        "language": "Hindi",
        "image": "https://wallpaperaccess.com/full/9335215.jpg",
        "rating": 4.4
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Oppenheimer",
        "genre": "Drama",
        "language": "English",
        "image": "https://i.pinimg.com/originals/25/74/bc/2574bcaa1d5a9fe6a54e4fd058aefb55.jpg",
        "rating": 4.1
    }
]

for movie in initial_movies:
    movies_table.put_item(Item=movie)
    analytics_table.put_item(Item=default_analytics_payload(movie["id"]))

print("Initial movies and analytics seeded successfully.")

# ==========================================================
# ================= END RUN ONLY ONCE ======================
# ==========================================================

# ================= PUBLIC =================
@app.route("/")
def home():
    return render_template("index.html", logged_in=is_logged_in())

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")


# ================= AUTH =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        favorite_genre = request.form["favorite_genre"]
        age_group = request.form["age_group"]

        # Check if user exists
        res = users_table.get_item(Key={"email": email})
        if "Item" in res:
            return "User already exists"

        users_table.put_item(Item={
            "email": email,
            "id": str(uuid.uuid4()),
            "name": name,
            "password": password,
            "favorite_genre": favorite_genre,
            "age_group": age_group,
            "favorites": []
        })

        send_notification(
            "New User Registration",
            f"User {name} ({email}) registered on CinemaPulse."
        )

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        res = users_table.get_item(Key={"email": email})
        user = res.get("Item")

        if user and user["password"] == password:
            session["user_email"] = email
            send_notification(
                "User Login",
                f"User {email} logged into CinemaPulse."
            )
            return redirect(url_for("user_dashboard"))

        return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ================= FAVORITE TOGGLE =================
@app.route("/movie/favorite/toggle/<movie_id>", methods=["POST"])
def toggle_favorite(movie_id):
    if not is_logged_in():
        return jsonify({"success": False, "message": "Not logged in"}), 401

    email = session["user_email"]
    res = users_table.get_item(Key={"email": email})
    user = res.get("Item")

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    favorites = user.get("favorites", [])

    if movie_id in favorites:
        favorites.remove(movie_id)
        is_favorite = False
    else:
        favorites.append(movie_id)
        is_favorite = True

    users_table.update_item(
        Key={"email": email},
        UpdateExpression="SET favorites = :f",
        ExpressionAttributeValues={":f": favorites}
    )

    return jsonify({
        "success": True,
        "is_favorite": is_favorite,
        "total_favorites": len(favorites)
    })


# ================= USER DASHBOARD =================
@app.route("/user/dashboard")
def user_dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))

    email = session["user_email"]
    user = users_table.get_item(Key={"email": email}).get("Item")

    if not user:
        return redirect(url_for("logout"))

    favorites = user.get("favorites", [])

    # Fetch all movies
    movies_res = movies_table.scan()
    movies = movies_res.get("Items", [])

    # Fetch all feedbacks
    feedbacks_res = feedbacks_table.scan()
    all_feedbacks = feedbacks_res.get("Items", [])

    # User feedbacks
    user_feedbacks = [f for f in all_feedbacks if f["user_email"] == email]

    movies_payload = []

    for movie in movies:
        movie_id = movie["id"]

        movie_feedbacks = sorted(
            [f for f in all_feedbacks if f["movie_id"] == movie_id],
            key=lambda fb: fb["timestamp"],
            reverse=True
        )

        avg_rating = movie.get("rating", 0.0)
        if movie_feedbacks:
            avg_rating = round(sum(fb["rating"] for fb in movie_feedbacks) / len(movie_feedbacks), 1)

        analytics_res = analytics_table.get_item(Key={"movie_id": movie_id})
        analytics = analytics_res.get("Item", default_analytics_payload(movie_id))

        movies_payload.append({
            **movie,
            "avg_rating": avg_rating,
            "feedbacks": movie_feedbacks,
            "analytics": analytics,
            "is_favorite": movie_id in favorites
        })

    favorite_movies = [m for m in movies_payload if m["is_favorite"]]

    feedback_history = []
    for fb in sorted(user_feedbacks, key=lambda item: item["timestamp"], reverse=True):
        movie_name = next((m["name"] for m in movies_payload if m["id"] == fb["movie_id"]), "Unknown")
        feedback_history.append({**fb, "movie_name": movie_name})

    stats = {
        "total_movies": len(movies_payload),
        "total_reviews": len(user_feedbacks),
        "total_favorites": len(favorites)
    }

    return render_template(
        "user_dashboard.html",
        user=user,
        movies=movies_payload,
        favorites=favorite_movies,
        feedback_history=feedback_history,
        stats=stats
    )


# ================= ADD FEEDBACK =================
@app.route("/movie/feedback/add", methods=["POST"])
def add_feedback():
    if not is_logged_in():
        return redirect(url_for("login"))

    movie_name = request.form["movie_name"]
    rating = int(request.form["rating"])
    comment = request.form["comment"]

    # Find movie by name
    movies_res = movies_table.scan()
    movies = movies_res.get("Items", [])

    movie = next((m for m in movies if m["name"].lower() == movie_name.lower()), None)
    if not movie:
        return redirect(url_for("user_dashboard"))

    sentiment = simple_sentiment_analysis(comment)

    feedback_id = str(uuid.uuid4())

    feedbacks_table.put_item(Item={
        "id": feedback_id,
        "user_email": session["user_email"],
        "movie_id": movie["id"],
        "rating": rating,
        "comment": comment,
        "sentiment": sentiment,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    # Update analytics + rating
    update_movie_analytics(movie["id"])
    update_movie_rating(movie["id"])

    send_notification(
        "New Feedback Added",
        f"""
User: {session['user_email']}
Movie: {movie_name}
Rating: {rating}
Sentiment: {sentiment}
Comment: {comment}
"""
    )

    return redirect(url_for("user_dashboard"))

# ================= ADMIN AUTH =================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Same hardcoded admin logic as your local app
        if email == "admin@example.com" and password == "admin123":
            session["admin_logged_in"] = True
            send_notification(
                "Admin Login",
                f"Admin logged in using {email}"
            )
            return redirect(url_for("admin_dashboard"))

        return "Invalid admin credentials"

    return render_template("admin_login.html")


# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    # Fetch all movies
    movies_res = movies_table.scan()
    movies = movies_res.get("Items", [])

    # Fetch all feedbacks
    feedbacks_res = feedbacks_table.scan()
    feedbacks = feedbacks_res.get("Items", [])

    # Fetch all analytics
    analytics_res = analytics_table.scan()
    analytics_items = analytics_res.get("Items", [])
    analytics_dict = {a["movie_id"]: a for a in analytics_items}

    movies_with_feedbacks = {}

    for movie in movies:
        movie_id = movie["id"]
        key = movie["name"].lower().replace(" ", "_")

        movies_with_feedbacks[key] = {
            **movie,
            "feedbacks": [f for f in feedbacks if f["movie_id"] == movie_id],
            "analytics": analytics_dict.get(movie_id, {})
        }

    return render_template(
        "admin_dashboard.html",
        movies=movies_with_feedbacks,
        analytics=analytics_dict
    )


# ================= ADMIN MOVIE CRUD =================
@app.route("/admin/movie/add", methods=["POST"])
def add_movie():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    name = request.form["name"]
    genre = request.form["genre"]
    language = request.form["language"]
    image = request.form["image"]
    rating = 0.0

    movie_id = str(uuid.uuid4())

    new_movie = {
        "id": movie_id,
        "name": name,
        "genre": genre,
        "language": language,
        "image": image,
        "rating": rating
    }

    movies_table.put_item(Item=new_movie)

    # Initialize analytics for new movie
    analytics_table.put_item(Item=default_analytics_payload(movie_id))

    send_notification(
        "New Movie Added",
        f"Admin added a new movie:\n{name}\nGenre: {genre}\nLanguage: {language}"
    )

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/movie/update", methods=["POST"])
def update_movie():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    old_name = request.form["old_name"]
    name = request.form["name"]
    genre = request.form["genre"]
    language = request.form["language"]
    image = request.form["image"]

    # Find movie by old name
    movies_res = movies_table.scan()
    movies = movies_res.get("Items", [])

    movie = next((m for m in movies if m["name"].lower() == old_name.lower()), None)

    if movie:
        movies_table.update_item(
            Key={"id": movie["id"]},
            UpdateExpression="SET #n = :n, genre = :g, language = :l, image = :i",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={
                ":n": name,
                ":g": genre,
                ":l": language,
                ":i": image
            }
        )

        # Recalculate rating (based only on feedbacks)
        update_movie_rating(movie["id"])

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/movie/delete", methods=["POST"])
def delete_movie():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    name = request.form["name"]

    # Find movie by name
    movies_res = movies_table.scan()
    movies = movies_res.get("Items", [])
    movie = next((m for m in movies if m["name"].lower() == name.lower()), None)

    if movie:
        movie_id = movie["id"]

        # Delete movie
        movies_table.delete_item(Key={"id": movie_id})

        # Delete related analytics
        analytics_table.delete_item(Key={"movie_id": movie_id})

        # Delete related feedbacks
        feedbacks_res = feedbacks_table.scan()
        feedbacks = feedbacks_res.get("Items", [])
        for f in feedbacks:
            if f["movie_id"] == movie_id:
                feedbacks_table.delete_item(Key={"id": f["id"]})

        send_notification(
            "Movie Deleted",
            f"Admin deleted movie: {name}"
        )

    return redirect(url_for("admin_dashboard"))


# ================= ADMIN FEEDBACK DELETE =================
@app.route("/admin/feedback/delete", methods=["POST"])
def delete_feedback():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    feedback_id = request.form["feedback_id"]

    # Find feedback
    res = feedbacks_table.get_item(Key={"id": feedback_id})
    feedback = res.get("Item")

    if feedback:
        movie_id = feedback["movie_id"]

        # Delete feedback
        feedbacks_table.delete_item(Key={"id": feedback_id})

        # Update analytics and rating
        update_movie_analytics(movie_id)
        update_movie_rating(movie_id)

    return redirect(url_for("admin_dashboard"))


# ================= FINAL RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

