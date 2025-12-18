from app import db # Assumes 'db' is initialized in your 'app.py'
from datetime import date, datetime, timezone
from sqlalchemy.schema import UniqueConstraint # Import for defining compound unique keys

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    fallback_strategy = db.Column(db.String(50), default="hold_cash")  # "hold_cash", "switch_best", "switch_safe"
    fallback_asset = db.Column(db.String(20), nullable=True)
    blocked = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships will be added implicitly via backrefs from other models

class Portfolio(db.Model):
    __tablename__ = "portfolios"
    # The primary key is the user_id, as each user has only one portfolio summary
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    cash_balance = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    total_invested = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    
    # Relationship back to the User model
    user = db.relationship("User", backref=db.backref("portfolio_summary", lazy=True))

    def __repr__(self):
        return f"<Portfolio user_id={self.user_id} cash_balance={self.cash_balance}>"

class Holding(db.Model):
    __tablename__ = 'holdings'
    holding_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ticker = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Numeric(10, 2), nullable=False)
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sector = db.Column(db.String(50)) # Used for Asset Allocation breakdown
    
    # Relationship back to the User model
    user = db.relationship("User", backref=db.backref("holdings", lazy=True))

    def __repr__(self):
        return f'<Holding {self.ticker} x {self.quantity} (User:{self.user_id})>'

# ----------------- Core Functionality Models Added ------------------

class Threshold(db.Model):
    """Stores user-defined safety limits for stocks."""
    __tablename__ = 'thresholds'
    threshold_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ticker = db.Column(db.String(10), nullable=False)
    min_price = db.Column(db.Numeric(10, 2), nullable=False)
    alert_enabled = db.Column(db.Boolean, nullable=False, default=True)
    
    user = db.relationship("User", backref=db.backref("thresholds", lazy=True))

    # Constraint ensures a user can only set one threshold per stock ticker
    __table_args__ = (
        UniqueConstraint('user_id', 'ticker', name='_user_ticker_threshold_uc'),
    )

    def __repr__(self):
        return f'<Threshold {self.ticker} Min: {self.min_price}>'

class PortfolioHistory(db.Model):
    """Stores daily snapshots of total portfolio value for graphing."""
    __tablename__ = "portfolio_history"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    total_value = db.Column(db.Numeric(12, 2), nullable=False)
    
    user = db.relationship("User", backref=db.backref("history", lazy=True))

    # Constraint ensures only one value is logged per user per day
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='_user_date_snapshot_uc'),
    )

    def __repr__(self):
        return f"<History User:{self.user_id} Date:{self.date} Value:{self.total_value}>"
    

class SwitchingRule(db.Model):
    __tablename__ = 'switching_rule'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    
    # Primary investment details (the one currently held)
    primary_ticker = db.Column(db.String(10), nullable=False)
    switch_threshold = db.Column(db.Float, nullable=False)
    
    # Backup investment details
    backup_ticker_1 = db.Column(db.String(10), nullable=True)
    backup_ticker_2 = db.Column(db.String(10), nullable=True) # Optional secondary backup

    def __repr__(self):
        return f"<SwitchingRule Primary:{self.primary_ticker} Backups:{self.backup_ticker_1}/{self.backup_ticker_2}>"
    

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    