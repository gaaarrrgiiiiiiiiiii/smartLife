from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from app import db, mail
from app.models import User, Admin, Holding, Portfolio

auth_bp = Blueprint("auth", __name__, template_folder="../templates")

# ---------------- USER AUTH ----------------

@auth_bp.route("/")
def login_page():
    return render_template("login.html")

@auth_bp.route("/signup-page")
def signup_page():
    return render_template("signup.html")

@auth_bp.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password")

    if not name or not email or not password:
        flash("All fields are required.", "danger")
        return redirect(url_for("auth.signup_page"))

    if User.query.filter_by(email=email).first():
        flash("User already exists.", "warning")
        return redirect(url_for("auth.signup_page"))

    hashed_pw = generate_password_hash(password)
    new_user = User(name=name, email=email, password=hashed_pw)

    db.session.add(new_user)
    db.session.commit()
    flash("Account created successfully. Please log in.", "success")

    return redirect(url_for("auth.login_page"))

@auth_bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        session["user_id"] = user.id
        session["user_name"] = user.name
        return redirect(url_for("profile.profile"))

    flash("Invalid email or password.", "danger")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login_page"))


# ---------------- ADMIN AUTH ----------------

@auth_bp.route("/admin-login-page")
def admin_login_page():
    return render_template("admin_login.html")

@auth_bp.route("/admin-login", methods=["POST"])
def admin_login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password")

    admin = Admin.query.filter_by(email=email).first()

    if not admin:
        flash("Admin not found.", "danger")
        return render_template("admin_login.html")

    # ✅ Simple plain-text password check
    if admin.password_hash == password:  
        session["admin_id"] = admin.id
        session["admin_email"] = admin.email
        flash("Welcome back, Admin!", "success")
        return redirect(url_for("auth.admin_dashboard"))

    flash("Invalid admin credentials.", "danger")
    return render_template("admin_login.html")

@auth_bp.route("/admin-logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_email", None)
    flash("Admin logged out successfully.", "info")
    return redirect(url_for("auth.login_page"))


# ---------------- ADMIN DASHBOARD ----------------

@auth_bp.route("/admin-dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        flash("Please log in as admin first.", "warning")
        return redirect(url_for("auth.admin_login_page"))

    users = User.query.all()
    user_data = []

    for user in users:
        holdings = Holding.query.filter_by(user_id=user.id).all()
        portfolio = Portfolio.query.filter_by(user_id=user.id).first()

        user_data.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "blocked": user.blocked,
            "holdings": holdings,
            "portfolio": portfolio,
        })

    return render_template("admin_dashboard.html", users=user_data)


# ---------------- ADMIN ACTIONS ----------------

@auth_bp.route("/block/<int:user_id>")
def block_user(user_id):
    if "admin_id" not in session:
        return redirect(url_for("auth.admin_login_page"))

    user = User.query.get_or_404(user_id)
    user.blocked = not user.blocked
    db.session.commit()

    status = "blocked" if user.blocked else "unblocked"
    flash(f"User {user.name} has been {status}.", "info")
    return redirect(url_for("auth.admin_dashboard"))


@auth_bp.route("/delete/<int:user_id>")
def delete_user(user_id):
    if "admin_id" not in session:
        return redirect(url_for("auth.admin_login_page"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.name} deleted successfully.", "success")

    return redirect(url_for("auth.admin_dashboard"))


@auth_bp.route("/send-email/<int:user_id>", methods=["POST"])
def send_email_to_user(user_id):
    if "admin_id" not in session:
        return redirect(url_for("auth.admin_login_page"))

    user = User.query.get_or_404(user_id)
    message_text = request.form.get("message")

    if not message_text:
        flash("Please enter a message before sending.", "warning")
        return redirect(url_for("auth.admin_dashboard"))

    try:
        msg = Message(
            subject="Message from Admin",
            sender="gargith24@gmail.com",
            recipients=[user.email],
            body=message_text,
        )
        mail.send(msg)
        flash(f"Email sent to {user.email}", "success")
    except Exception as e:
        flash(f"Error sending email: {str(e)}", "danger")

    return redirect(url_for("auth.admin_dashboard"))





@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    email = request.form.get("email", "").strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("No account found with that email.", "danger")
        return redirect(url_for("auth.login_page"))

    import random, string
    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    user.password_hash = temp_password
    db.session.commit()

    try:
        msg = Message(
            subject="Temporary Password",
            recipients=[email],
            body=f"Your temporary password is: {temp_password}\n\nPlease log in and change it immediately.",
            sender="gargith24@gmail.com"
        )
        mail.send(msg)
        flash("Temporary password sent to your email.", "success")
    except Exception as e:
        flash(f"Error sending email: {str(e)}", "danger")

    return redirect(url_for("auth.login_page"))

