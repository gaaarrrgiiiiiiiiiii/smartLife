# profile_routes.py

from flask import Blueprint, session, render_template, redirect, url_for, request
from app.models import User, Portfolio, Holding, PortfolioHistory
from app import db
from decimal import Decimal
import yfinance as yf
from datetime import date

profile_bp = Blueprint("profile", __name__, template_folder="../templates")


# ----------------- Portfolio Calculation & Logging -----------------

def calculate_live_portfolio_value(user_id):
    """Calculate total portfolio value including cash and holdings."""
    portfolio = Portfolio.query.filter_by(user_id=user_id).first()
    cash_balance = Decimal(portfolio.cash_balance) if portfolio else Decimal('0.00')

    holdings = Holding.query.filter_by(user_id=user_id).all()
    holdings_value = Decimal('0.00')

    for h in holdings:
        try:
            stock = yf.Ticker(h.ticker)
            current_price = stock.history(period="1d")['Close'][-1]
            current_price = Decimal(str(current_price))
            holdings_value += current_price * h.quantity
        except Exception as e:
            print(f"Error fetching {h.ticker}: {e}")

    total_value = cash_balance + holdings_value
    return total_value.quantize(Decimal('0.01'))


def log_daily_portfolio_snapshot(user_id):
    """Logs today's portfolio value for the user. Updates if snapshot exists."""
    total_value = calculate_live_portfolio_value(user_id)
    existing = PortfolioHistory.query.filter_by(user_id=user_id, date=date.today()).first()

    if existing:
        existing.total_value = total_value
    else:
        snapshot = PortfolioHistory(
            user_id=user_id,
            date=date.today(),
            total_value=total_value
        )
        db.session.add(snapshot)

    db.session.commit()


# ----------------- Profile Route -----------------

@profile_bp.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login_page"))

    user = User.query.filter_by(id=session["user_id"]).first()
    if not user:
        return redirect(url_for("auth.login_page"))

    joined_on = user.created_at.strftime("%m/%d/%Y")
    user_email = user.email

    portfolio = Portfolio.query.filter_by(user_id=user.id).first()
    cash_balance = Decimal(portfolio.cash_balance).quantize(Decimal('0.01')) if portfolio else Decimal('0.00')
    total_invested = Decimal(portfolio.total_invested).quantize(Decimal('0.01')) if portfolio else Decimal('0.00')

    # Fetch all holdings
    holdings = Holding.query.filter_by(user_id=user.id).all()
    holdings_list = []
    total_holdings_value = Decimal('0.00')

    for h in holdings:
        try:
            stock = yf.Ticker(h.ticker)
            current_price = Decimal(str(stock.history(period="1d")['Close'][-1])).quantize(Decimal('0.01'))
            holding_value = (current_price * h.quantity).quantize(Decimal('0.01'))
            total_holdings_value += holding_value

            holdings_list.append({
                "ticker": h.ticker,
                "quantity": h.quantity,
                "current_price": current_price,
                "holding_value": holding_value,
                "sector": h.sector or "Unknown"
            })
        except Exception as e:
            print(f"Error fetching {h.ticker}: {e}")

    total_portfolio_value = (cash_balance + total_holdings_value).quantize(Decimal('0.01'))

    # --- Log or update daily snapshot ---
    log_daily_portfolio_snapshot(user.id)

    # --- Fetch portfolio history for graph ---
    history = PortfolioHistory.query.filter_by(user_id=user.id).order_by(PortfolioHistory.date).all()
    portfolio_history_dates = [h.date.strftime("%m/%d") for h in history]
    portfolio_history_values = [float(h.total_value) for h in history]

    # --- Asset allocation (for pie chart) ---
    asset_labels = []
    asset_values = []

    if holdings_list:
        sector_map = {}
        for h in holdings_list:
            sector_map[h["sector"]] = sector_map.get(h["sector"], Decimal("0.00")) + h["holding_value"]

        asset_labels = list(sector_map.keys())
        asset_values = [float(v) for v in sector_map.values()]
    
    # --- Weekly trend data for each holding ---
        stock_trends = {}
        for h in holdings:
            try:
                stock = yf.Ticker(h.ticker)
                hist = stock.history(period="7d")["Close"]
                stock_trends[h.ticker] = {
                    "dates": [d.strftime("%m/%d") for d in hist.index],
                    "prices": [float(p) for p in hist.values]
                }
            except Exception as e:
                print(f"Error fetching trend for {h.ticker}: {e}")


    # --- Render ---
    return render_template(
    "profile.html",
    name=user.name,
    joined_on=joined_on,
    user_email=user_email,
    cash_balance=cash_balance,
    total_invested=total_invested,
    holdings=holdings_list,
    total_portfolio_value=total_portfolio_value,
    portfolio_history_dates=portfolio_history_dates,
    portfolio_history_values=portfolio_history_values,
    asset_labels=asset_labels,
    asset_values=asset_values,
    stock_trends=stock_trends
)



# ----------------- Buy/Sell/Update Route -----------------

@profile_bp.route("/update_holding", methods=["POST"])
def update_holding():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login_page"))

    ticker = request.form.get("ticker").upper()
    quantity = int(request.form.get("quantity"))
    action = request.form.get("action")  # "buy" or "sell"

    portfolio = Portfolio.query.filter_by(user_id=user_id).first()
    if not portfolio:
        # Create portfolio if it doesn't exist
        portfolio = Portfolio(user_id=user_id, cash_balance=0, total_invested=0)
        db.session.add(portfolio)
        db.session.commit()

    # Fetch current stock price
    try:
        stock_price = Decimal(str(yf.Ticker(ticker).history(period="1d")['Close'][-1])).quantize(Decimal('0.01'))
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return redirect(url_for("profile.profile"))

    holding = Holding.query.filter_by(user_id=user_id, ticker=ticker).first()

    if action == "buy":
        total_cost = stock_price * quantity

        if portfolio.cash_balance < total_cost:
            # Not enough cash
            print("Insufficient funds")
            return redirect(url_for("profile.profile"))

        # Deduct cash
        portfolio.cash_balance -= total_cost
        portfolio.total_invested += total_cost

        if holding:
            # Update average purchase price
            old_total_cost = holding.purchase_price * holding.quantity
            new_quantity = holding.quantity + quantity
            holding.purchase_price = (old_total_cost + total_cost) / new_quantity
            holding.quantity = new_quantity
        else:
            holding = Holding(
                user_id=user_id,
                ticker=ticker,
                quantity=quantity,
                purchase_price=stock_price
            )
            db.session.add(holding)

    elif action == "sell":
        if not holding or holding.quantity < quantity:
            # Cannot sell more than you own
            print("Insufficient shares to sell")
            return redirect(url_for("profile.profile"))

        total_proceeds = stock_price * quantity
        portfolio.cash_balance += total_proceeds
        portfolio.total_invested -= holding.purchase_price * quantity

        holding.quantity -= quantity
        if holding.quantity == 0:
            db.session.delete(holding)

    db.session.commit()

    # Log/update daily portfolio snapshot after changes
    log_daily_portfolio_snapshot(user_id)

    return redirect(url_for("profile.profile"))
