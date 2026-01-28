from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_mail import Mail, Message

load_dotenv()  # loads .env file variables

app = Flask(__name__)
app.secret_key = "palak_cinemaPulse_secret_key"

# ================= USERS TABLE =================
users = {}

# ================= MOVIES TABLE =================
movies = {
    "jawan": {
        "id": str(uuid.uuid4()),
        "name": "Jawan",
        "genre": "Action",
        "language": "Hindi",
        "image": "https://wallpaperaccess.com/full/9335215.jpg",
        "rating": 4.4
    },
    "oppenheimer": {
        "id": str(uuid.uuid4()),
        "name": "Oppenheimer",
        "genre": "Drama",
        "language": "English",
        "image": "https://i.pinimg.com/originals/25/74/bc/2574bcaa1d5a9fe6a54e4fd058aefb55.jpg",
        "rating": 4.1
    }
}

# ================= FEEDBACK TABLE =================
feedbacks = [
    {
        "id": str(uuid.uuid4()),
        "user_email": "anonymous@cinemapulse.com",
        "movie_id": movies["jawan"]["id"],
        "rating": 4,
        "comment": "Amazing visuals and soundtrack!",
        "sentiment": "Positive",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    },
    {
        "id": str(uuid.uuid4()),
        "user_email": "anonymous@cinemapulse.com",
        "movie_id": movies["jawan"]["id"],
        "rating": 3,
        "comment": "Story was predictable but fun.",
        "sentiment": "Neutral",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    },
    {
        "id": str(uuid.uuid4()),
        "user_email": "anonymous@cinemapulse.com",
        "movie_id": movies["oppenheimer"]["id"],
        "rating": 5,
        "comment": "Masterpiece storytelling.",
        "sentiment": "Positive",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
]

# ================= MOVIE ANALYTICS TABLE =================
movie_analytics = {}

# ================= HELPERS =================

def default_analytics_payload():
    return {
        "score": 0,
        "breakdown": {"positive": 0, "neutral": 0, "negative": 0},
        "trend": "Stable",
        "last_updated": None
    }

def is_logged_in():
    return "user_email" in session

def get_feedbacks_for_movie(movie_id):
    return [f for f in feedbacks if f["movie_id"] == movie_id]

def get_feedbacks_for_user(user_email):
    return [f for f in feedbacks if f["user_email"] == user_email]

# ================= FAVORITE TOGGLE =================
@app.route("/movie/favorite/toggle/<movie_id>", methods=["POST"])
def toggle_favorite(movie_id):
    if not is_logged_in():
        return jsonify({"success": False, "message": "Not logged in"}), 401

    user = users.get(session["user_email"])
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    favorites = user.setdefault("favorites", [])

    if movie_id in favorites:
        favorites.remove(movie_id)
        is_favorite = False
    else:
        favorites.append(movie_id)
        is_favorite = True

    return jsonify({
        "success": True,
        "is_favorite": is_favorite,
        "total_favorites": len(favorites)
    })

# ================= EMAIL CONFIG =================
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_STARTTLS") == "True"
app.config['MAIL_USE_SSL'] = os.getenv("MAIL_SSL_TLS") == "True"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_FROM")

mail = Mail(app)


def send_email_notification(subject, message, to=None):
    try:
        if not to:
            to = [app.config['MAIL_DEFAULT_SENDER']]  # default admin mailbox

        msg = Message(subject, recipients=to)
        msg.body = message
        mail.send(msg)
        print(f"[EMAIL SENT] {subject}")
    except Exception as e:
        print("Email error:", e)

# ================= MOVIE RATING LOGIC =================
def update_movie_rating(movie_id):
    movie_feedbacks = [f for f in feedbacks if f["movie_id"] == movie_id]

    if not movie_feedbacks:
        new_rating = 0.0
    else:
        new_rating = round(
            sum(f["rating"] for f in movie_feedbacks) / len(movie_feedbacks),
            1
        )

    for movie in movies.values():
        if movie["id"] == movie_id:
            movie["rating"] = new_rating
            break


# Simple local sentiment (placeholder for AWS AI later)
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
def init_movie_analytics():
    for key, movie in movies.items():
        movie_analytics[movie["id"]] = default_analytics_payload()
        

def update_movie_analytics(movie_id):
    movie_feedbacks = [f for f in feedbacks if f["movie_id"] == movie_id]

    if not movie_feedbacks:
        movie_analytics[movie_id] = default_analytics_payload()
        return

    positive = sum(1 for f in movie_feedbacks if f["sentiment"] == "Positive")
    neutral  = sum(1 for f in movie_feedbacks if f["sentiment"] == "Neutral")
    negative = sum(1 for f in movie_feedbacks if f["sentiment"] == "Negative")
    total = len(movie_feedbacks)

    score = int((positive * 100 + neutral * 50 + negative * 10) / total)

    if score > 75:
        trend = "Trending Up"
    elif score > 50:
        trend = "Stable"
    else:
        trend = "Trending Down"

    movie_analytics[movie_id] = {
        "score": score,
        "breakdown": {
            "positive": int((positive / total) * 100),
            "neutral": int((neutral / total) * 100),
            "negative": int((negative / total) * 100)
        },
        "trend": trend,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# Initialize analytics
init_movie_analytics()
for f in feedbacks:
    update_movie_analytics(f["movie_id"])
    update_movie_rating(f["movie_id"])

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

        if email in users:
            return "User already exists"

        users[email] = {
            "id": str(uuid.uuid4()),
            "name": name,
            "password": password,
            "favorite_genre": favorite_genre,
            "age_group": age_group,
            "favorites": []
        }
        send_email_notification(
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

        user = users.get(email)
        if user and user["password"] == password:
            session["user_email"] = email
            send_email_notification(
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

# ================= USER DASHBOARD =================
@app.route("/user/dashboard")
def user_dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))

    user = users.get(session["user_email"])
    if not user:
        return redirect(url_for("logout"))

    favorites = user.setdefault("favorites", [])
    user_feedbacks = get_feedbacks_for_user(session["user_email"])

    movies_payload = []
    for movie in movies.values():
        movie_id = movie["id"]
        movie_feedbacks = sorted(
            get_feedbacks_for_movie(movie_id),
            key=lambda fb: fb["timestamp"],
            reverse=True
        )
        avg_rating = movie["rating"]
        if movie_feedbacks:
            avg_rating = round(sum(fb["rating"] for fb in movie_feedbacks) / len(movie_feedbacks), 1)

        analytics = movie_analytics.get(movie_id, default_analytics_payload())

        movies_payload.append({
            **movie,
            "avg_rating": avg_rating,
            "feedbacks": movie_feedbacks,
            "analytics": analytics,
            "is_favorite": movie_id in favorites
        })

    favorite_movies = [movie for movie in movies_payload if movie["is_favorite"]]

    feedback_history = []
    for fb in sorted(user_feedbacks, key=lambda item: item["timestamp"], reverse=True):
        movie_name = next((movie["name"] for movie in movies_payload if movie["id"] == fb["movie_id"]), "Unknown")
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

@app.route("/movie/feedback/add", methods=["POST"])
def add_feedback():
    if not is_logged_in():
        return redirect(url_for("login"))

    movie_name = request.form["movie_name"]
    rating = int(request.form["rating"])
    comment = request.form["comment"]

    key = movie_name.lower().replace(" ", "_")

    if key in movies:
        sentiment = simple_sentiment_analysis(comment)

        feedbacks.append({
            "id": str(uuid.uuid4()),
            "user_email": session["user_email"],
            "movie_id": movies[key]["id"],
            "rating": rating,
            "comment": comment,
            "sentiment": sentiment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        update_movie_analytics(movies[key]["id"])
        update_movie_rating(movies[key]["id"])

        send_email_notification(
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

        if email == "admin@example.com" and password == "admin123":
            session["admin_logged_in"] = True
            send_email_notification(
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

    movies_with_feedbacks = {}
    for key, movie in movies.items():
        movies_with_feedbacks[key] = {
            **movie,
            "feedbacks": get_feedbacks_for_movie(movie["id"]),
            "analytics": movie_analytics.get(movie["id"], {})
        }

    return render_template(
        "admin_dashboard.html",
        movies=movies_with_feedbacks,
        analytics=movie_analytics
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

    key = name.lower().replace(" ", "_")
    movie_id = str(uuid.uuid4())

    movies[key] = {
        "id": movie_id,
        "name": name,
        "genre": genre,
        "language": language,
        "image": image,
        "rating": rating
    }

    movie_analytics[movie_id] = default_analytics_payload()

    send_email_notification(
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

    old_key = old_name.lower().replace(" ", "_")
    new_key = name.lower().replace(" ", "_")

    if old_key in movies:
        movie_data = movies.pop(old_key)

        movie_data.update({
            "name": name,
            "genre": genre,
            "language": language,
            "image": image
        })

        movies[new_key] = movie_data

        # Recalculate rating based only on feedbacks
        update_movie_rating(movie_data["id"])

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/movie/delete", methods=["POST"])
def delete_movie():
    global feedbacks

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    name = request.form["name"]
    key = name.lower().replace(" ", "_")

    if key in movies:
        movie_id = movies[key]["id"]
        del movies[key]

        # Remove related feedbacks
        feedbacks = [f for f in feedbacks if f["movie_id"] != movie_id]

        # Remove analytics
        if movie_id in movie_analytics:
            del movie_analytics[movie_id]

        send_email_notification(
            "Movie Deleted",
            f"Admin deleted movie: {name}"
        )

    return redirect(url_for("admin_dashboard"))

# ================= ADMIN FEEDBACK DELETE =================
@app.route("/admin/feedback/delete", methods=["POST"])
def delete_feedback():
    global feedbacks

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    feedback_id = request.form["feedback_id"]
    movie_id = None

    for f in feedbacks:
        if f["id"] == feedback_id:
            movie_id = f["movie_id"]
            break

    feedbacks = [f for f in feedbacks if f["id"] != feedback_id]

    if movie_id:
        update_movie_analytics(movie_id)
        update_movie_rating(movie_id)

    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
