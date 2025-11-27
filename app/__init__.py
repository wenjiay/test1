# from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
# from config import Config
#
# db = SQLAlchemy()
# migrate = Migrate()
#
# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)
#
#     db.init_app(app)
#     migrate.init_app(app, db)
#
#     # 避免循环引用，在这里导入模型
#     from app.models import User, Quiz
#     with app.app_context():
#         db.create_all()
#
#     return app

import os

from flask import Flask, send_file
from flask_migrate import Migrate
from app.models import db,user_role
import app.models
from flask_login import LoginManager
from app.models import *
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)
    migrate.init_app(app, db)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        print(f"[DEBUG] Flask received filename = {filename}")
        cleaned_filename = filename.replace('\\', '/')
        abs_path = os.path.join(os.getcwd(), 'uploads', cleaned_filename)

        print('[DEBUG] Looking for file at:', abs_path)
        print('[DEBUG] File exists?', os.path.exists(abs_path))

        if not os.path.exists(abs_path):
            return "File not found", 404

        return send_file(abs_path, as_attachment=True)
 # # 注册蓝图
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.student import student_bp
    app.register_blueprint(student_bp)

    # 导入 utils 中的功能
    from app.utils.ai_utils import generate_questions_with_ai  # 替换为实际函数名
    from app.utils.file_utils import extract_text_from_file

    from app.routes.teacher import teacher_bp
    app.register_blueprint(teacher_bp)

    return app