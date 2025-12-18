SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:123456@localhost:3307/smartlife"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "supersecretkey"

MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = "add_your_own_mailid"
MAIL_PASSWORD = "add_your_own_app_password"
MAIL_DEFAULT_SENDER = MAIL_USERNAME