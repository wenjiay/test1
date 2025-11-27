import os


HOSTNAME = "127.0.0.1"
PORT = 3306
USERNAME = "root"
PASSWORD = "root"
DATABASE = "database_learn"

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "root")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")



