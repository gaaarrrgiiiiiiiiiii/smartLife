# app/threshold.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.models import db, User, Threshold
import yfinance as yf
import numpy as np
from sklearn.linear_model import LogisticRegression
from datetime import date, timedelta

threshold_bp = Blueprint("threshold", __name__)

# ---------------- Helper Functions ----------------
def get_trend_data(ticker, days=30):
    """
    Return historical close prices as 1D numpy array for last `days`.
    """
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None
        return np.array(data["Close"].values).flatten()
    except Exception:
        return None

def suggest_threshold(ticker):
    """
    Use logistic regression to suggest threshold.
    Returns None if insufficient data.
    """
    prices = get_trend_data(ticker, days=30)
    if prices is None or len(prices) < 5:
        return None  # insufficient data

    # Prepare features and labels
    X = prices[:-1].reshape(-1, 1)  # yesterday's price
    y = (prices[1:] > prices[:-1]).astype(int)  # 1 if next day price goes up

    # Train logistic regression
    try:
        model = LogisticRegression(solver="liblinear")
        model.fit(X, y)
        last_price = float(prices[-1])
        prob_up = model.predict_proba(np.array([[last_price]]))[0][1]
        suggested = last_price * (0.95 if prob_up > 0.6 else 1.05)
        return round(suggested, 2)
    except Exception:
        return None

def compute_trend_strength(ticker):
    """
    Lightweight metric for 'strength' used by 'switch_best' strategy.
    Returns average daily return over the last 14 trading days.
    """
    prices = get_trend_data(ticker, days=30)
    if prices is None or len(prices) < 6:
        return None
    # compute daily returns
    returns = np.diff(prices) / prices[:-1]
    # use recent 14 points if available
    recent = returns[-14:] if len(returns) >= 14 else returns
    return float(np.nanmean(recent))

def handle_breakdown(user, broken_ticker, portfolio_tickers):
    """
    Decide what to do when `broken_ticker` falls below its threshold.
    - user: User model instance
    - broken_ticker: ticker string that broke down
    - portfolio_tickers: list of tickers user currently holds (strings)
    Returns a dict describing the action:
      {"action": "sell_to_cash"} or
      {"action": "switch_to", "target": "<ticker>"}
    """
    strategy = (user.fallback_strategy or "hold_cash").lower()

    if strategy == "hold_cash":
        return {"action": "sell_to_cash"}

    if strategy == "switch_safe":
        target = (user.fallback_asset or "SPY").upper()
        return {"action": "switch_to", "target": target}

    if strategy == "switch_best":
        # evaluate trend strength for each ticker in portfolio, excluding broken
        best = None
        best_strength = -float("inf")
        for t in portfolio_tickers:
            t_up = t.upper()
            if t_up == broken_ticker.upper():
                continue
            strength = compute_trend_strength(t_up)
            if strength is None:
                continue
            if strength > best_strength:
                best_strength = strength
                best = t_up
        # fallback if no valid best found
        if best:
            return {"action": "switch_to", "target": best}
        else:
            # fallback to safe asset if nothing obvious
            return {"action": "switch_to", "target": (user.fallback_asset or "SPY").upper()}

    # default safe
    return {"action": "sell_to_cash"}

# ---------------- Routes ----------------
@threshold_bp.route("/thresholds")
def thresholds():
    if "user_id" not in session:
        return redirect(url_for("auth.login_page"))

    user_id = session["user_id"]
    user = User.query.get(user_id)
    thresholds = Threshold.query.filter_by(user_id=user_id).all()

    thresholds_enabled = [t for t in thresholds if t.min_price is not None]
    thresholds_disabled = [t for t in thresholds if t.min_price is None]

    return render_template(
        "nav.html",
        user=user,
        thresholds_enabled=thresholds_enabled,
        thresholds_disabled=thresholds_disabled
    )

@threshold_bp.route("/thresholds/update/<ticker>", methods=["GET", "POST"])
def update_threshold_page(ticker):
    if "user_id" not in session:
        return redirect(url_for("auth.login_page"))

    user_id = session["user_id"]
    user = User.query.get(user_id)
    threshold = Threshold.query.filter_by(user_id=user_id, ticker=ticker.upper()).first()
    current_value = threshold.min_price if threshold else None

    suggested = suggest_threshold(ticker)

    if request.method == "POST":
        new_value = request.form.get("threshold")
        if not new_value:
            return render_template(
                "update_threshold.html",
                ticker=ticker.upper(),
                current_value=current_value,
                suggested=suggested,
                error="Please enter a value"
            )
        try:
            new_value = float(new_value)
        except ValueError:
            return render_template(
                "update_threshold.html",
                ticker=ticker.upper(),
                current_value=current_value,
                suggested=suggested,
                error="Invalid numeric value"
            )

        if not threshold:
            threshold = Threshold(user_id=user_id, ticker=ticker.upper(), min_price=new_value)
            db.session.add(threshold)
        else:
            threshold.min_price = new_value
        db.session.commit()
        flash("Threshold updated", "success")
        return redirect(url_for("threshold.thresholds"))

    return render_template(
        "update_threshold.html",
        ticker=ticker.upper(),
        current_value=current_value,
        suggested=suggested
    )

@threshold_bp.route("/thresholds/settings", methods=["GET", "POST"])
def threshold_settings():
    if "user_id" not in session:
        return redirect(url_for("auth.login_page"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        selected_strategy = request.form.get("strategy")
        fallback_asset = request.form.get("fallback_asset")

        if selected_strategy not in ("hold_cash", "switch_best", "switch_safe"):
            flash("Invalid strategy selection", "error")
            return redirect(url_for("threshold.threshold_settings"))

        user.fallback_strategy = selected_strategy
        user.fallback_asset = fallback_asset.strip().upper() if fallback_asset else None
        db.session.commit()
        flash("✅ Fallback strategy updated successfully!", "success")
        return redirect(url_for("threshold.thresholds"))

    return render_template(
        "update_threshold.html",
        ticker=None,  # optional placeholder (template compatibility)
        current_value=None,
        suggested=None,
        current_strategy=user.fallback_strategy,
        current_asset=user.fallback_asset,
        settings_mode=True  # lets template know it's showing strategy settings
    )

