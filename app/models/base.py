from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
from datetime import datetime

class User(UserMixin,db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    role = db.Column(db.String(32), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    password = db.Column(db.String(128))

    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': role
    }

    @staticmethod
    def login(name, password):
        user = User.query.filter_by(name=name).first()
        if user and user.password == password:
            return user
        return None
