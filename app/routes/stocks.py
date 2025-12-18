from flask import Blueprint, render_template, session, redirect
from app.models import db, Holding
import yfinance as yf
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import numpy as np
from sklearn.linear_model import LinearRegression

stocks_bp = Blueprint("stocks", __name__)

# Example top stocks list
TOP_STOCKS = [
    # ---------- Technology ----------
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology",
     "description": "World’s largest tech company, leading in iPhones, Macs, and wearables.",
     "logo": "appl.png"},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "sector": "Technology",
     "description": "Global leader in software, cloud computing, and enterprise solutions.",
     "logo": "microsoft.png"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology",
     "description": "Parent of Google, driving innovation in AI, cloud, and advertising.",
     "logo": "google.png"},
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology",
     "description": "Dominant in GPUs powering gaming, AI, and data center workloads.",
     "logo": "nvidia.jpeg"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Technology",
     "description": "E-commerce and cloud leader through AWS and global retail network.",
     "logo": "amazon.jpeg"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Technology",
     "description": "Owns Facebook, Instagram, and WhatsApp, investing heavily in metaverse.",
     "logo": "meta.jpg"},
    {"ticker": "ADBE", "name": "Adobe Inc.", "sector": "Technology",
     "description": "Known for Photoshop, Acrobat, and digital media software innovations.",
     "logo": "adobe.jpg"},
    {"ticker": "CRM", "name": "Salesforce Inc.", "sector": "Technology",
     "description": "Pioneer in CRM and cloud-based enterprise business solutions.",
     "logo": "salesforce.png"},
    {"ticker": "INTC", "name": "Intel Corp.", "sector": "Technology",
     "description": "Semiconductor giant producing CPUs and advancing AI chip research.",
     "logo": "intel.jpg"},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "sector": "Technology",
     "description": "High-performance chipmaker rivaling Intel and NVIDIA in computing.",
     "logo": "amd.jpg"},

    # ---------- Finance ----------
    {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Finance",
     "description": "Leading global bank offering investment and retail financial services.",
     "logo": "jpmorgan.png"},
    {"ticker": "V", "name": "Visa Inc.", "sector": "Finance",
     "description": "Operates world’s largest payment processing network.",
     "logo": "visa.png"},
    {"ticker": "MA", "name": "Mastercard Inc.", "sector": "Finance",
     "description": "Global digital payments firm enabling secure financial transactions.",
     "logo": "mastercard.png"},
    {"ticker": "BAC", "name": "Bank of America", "sector": "Finance",
     "description": "Major U.S. bank providing consumer and corporate financial services.",
     "logo": "bofa.png"},
    {"ticker": "GS", "name": "Goldman Sachs", "sector": "Finance",
     "description": "Investment bank focused on wealth management and trading operations.",
     "logo": "goldman.png"},

    # ---------- Healthcare ----------
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare",
     "description": "Multinational firm in pharmaceuticals, medical devices, and consumer goods.",
     "logo": "jnj.png"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare",
     "description": "Global pharmaceutical leader known for vaccines and innovative therapies.",
     "logo": "pfizer.png"},
    {"ticker": "UNH", "name": "UnitedHealth Group", "sector": "Healthcare",
     "description": "Top U.S. health insurer integrating care and data-driven services.",
     "logo": "unh.png"},
    {"ticker": "MRNA", "name": "Moderna Inc.", "sector": "Healthcare",
     "description": "Biotech company advancing mRNA vaccines and therapeutics.",
     "logo": "moderna.png"},

    # ---------- Energy ----------
    {"ticker": "XOM", "name": "Exxon Mobil Corp.", "sector": "Energy",
     "description": "Largest publicly traded oil and gas company expanding into renewables.",
     "logo": "exonn.png"},
    {"ticker": "CVX", "name": "Chevron Corp.", "sector": "Energy",
     "description": "Diversified energy firm focused on oil, gas, and sustainable fuel projects.",
     "logo": "chevron.jpg"},
    {"ticker": "NEE", "name": "NextEra Energy", "sector": "Energy",
     "description": "U.S. leader in renewable energy generation and clean utilities.",
     "logo": "nextera.png"},
    {"ticker": "BP", "name": "BP Plc", "sector": "Energy",
     "description": "British energy company transitioning toward sustainable operations.",
     "logo": "bp.jpg"},

    # ---------- Consumer ----------
    {"ticker": "KO", "name": "Coca-Cola Co.", "sector": "Consumer",
     "description": "Global beverage leader with brands like Coke, Sprite, and Fanta.",
     "logo": "cocola.jpg"},
    {"ticker": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer",
     "description": "Diversified food and beverage company owning Pepsi, Lay’s, and Quaker.",
     "logo": "pepsi.png"},
    {"ticker": "NKE", "name": "Nike Inc.", "sector": "Consumer",
     "description": "World’s leading sportswear and athletic footwear brand.",
     "logo": "nike.jpg"},
    {"ticker": "MCD", "name": "McDonald's Corp.", "sector": "Consumer",
     "description": "Global fast-food giant with extensive franchise network.",
     "logo": "mcdonalds.png"},

    # ---------- Automotive ----------
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Automotive",
     "description": "Electric vehicle pioneer advancing autonomous and energy products.",
     "logo": "tesla.png"},
    {"ticker": "F", "name": "Ford Motor Co.", "sector": "Automotive",
     "description": "Historic carmaker accelerating EV production and smart mobility.",
     "logo": "ford.jpg"},
    {"ticker": "GM", "name": "General Motors", "sector": "Automotive",
     "description": "U.S. auto giant investing in electric and self-driving vehicles.",
     "logo": "gm.jpg"},
]


def fetch_stock_trend(ticker):
    """Fetch last 7 days and compute trend, return base64 image and trend text."""
    try:
        data = yf.download(ticker, period="7d", progress=False, auto_adjust=True)
        if data.empty:
            return None, "No data"

        # Linear regression trend
        X = np.arange(len(data)).reshape(-1, 1)
        y = data["Close"].values.reshape(-1, 1)
        model = LinearRegression().fit(X, y)
        slope = model.coef_[0][0]
        trend_text = "📈 Uptrend" if slope > 0 else "📉 Downtrend"

        # Plot trend graph
        plt.figure(figsize=(3, 1.5))
        plt.plot(data['Close'], color='green' if data['Close'].iloc[-1] >= data['Close'].iloc[0] else 'red')
        plt.xticks([], [])
        plt.yticks([], [])
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', transparent=True)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()

        return img_base64, trend_text

    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None, "Error"

@stocks_bp.route("/top-stocks")
def top_stocks():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    user_stocks = [s.ticker for s in Holding.query.filter_by(user_id=user_id).all()]

    top_stocks_data = []

    for stock in TOP_STOCKS:
        if stock["ticker"] in user_stocks:
            continue  # skip stocks already owned

        trend_graph, trend_text = fetch_stock_trend(stock["ticker"])

        # You can fetch logos from Yahoo Finance or use a placeholder
       

        top_stocks_data.append({
            "ticker": stock["ticker"],
            "name": stock["name"],
            "sector": stock["sector"],
            "description": stock["description"],
            "trend": trend_text,
            "trend_graph": trend_graph,
            "logo": stock["logo"]
        })

    return render_template("top_stocks.html", stocks=top_stocks_data)
