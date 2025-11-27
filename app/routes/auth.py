from app.models.base import User
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from flask_login import login_user,logout_user, login_required, current_user
import random, time



auth_bp = Blueprint('auth', __name__,url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')
@auth_bp.route('/login_by_password', methods=['POST'])
def login_by_password():
    name = request.form['name']
    password = request.form['password']
    user = User.login(name, password)

    if not user:
        flash("账号或密码错误")
        return redirect(url_for('auth.login'))

    login_user(user)

    # 根据身份跳转
    if user.role == 'Student':
        return redirect(url_for('student.student_home'))
    elif user.role == 'Teacher':
        return redirect(url_for('teacher.teacher_home'))  # 替换为你实际有的路径
    else:
        flash("未知用户身份")
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
