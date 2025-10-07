from flask import Blueprint, session, render_template, redirect, url_for
import requests

news_bp = Blueprint("news", __name__, template_folder="../templates")

NEWS_API_KEY = "e6fcbb7c9f3740c5b3d2ae7e4386a729"  # replace with your API key

@news_bp.route("/news")
def news():
    if "user_id" not in session:
        return redirect(url_for("auth.login_page"))

    # Fetch latest stock news
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "stocks OR market OR finance",
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        news_data = response.json().get("articles", [])
    except Exception as e:
        print("Error fetching news:", e)
        news_data = []

    # Pass news to template
    return render_template("news.html", name=session["user_name"], news=news_data)






#4ZNQLuNnOCS3V964aIuH4mOQPPJIbrxu api key




