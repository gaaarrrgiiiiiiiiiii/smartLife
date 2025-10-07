from flask import Blueprint, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__, template_folder="../templates")

# ---------------- RENDER PAGES ----------------
@auth_bp.route("/")
def login_page():
    return render_template("login.html")

@auth_bp.route("/signup-page")
def signup_page():
    return render_template("signup.html")

# ---------------- SIGNUP ----------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name").strip()
    email = request.form.get("email").strip().lower()
    password = request.form.get("password")

    if not name or not email or not password:
        return "Missing fields", 400

    if User.query.filter_by(email=email).first():
        return "User already exists", 400

    hashed_pw = generate_password_hash(password)
    new_user = User(name=name, email=email, password=hashed_pw)
    
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for("auth.login_page"))

# ---------------- LOGIN ----------------
@auth_bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("email").strip().lower()
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        session["user_id"] = user.id
        session["user_name"] = user.name
        return redirect(url_for("profile.profile"))  # redirect to profile page

    return render_template("login.html", error="Invalid credentials")

# ---------------- LOGOUT ----------------
@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    return redirect(url_for("auth.login_page"))
