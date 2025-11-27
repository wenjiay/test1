# app/routes/teacher.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.base import User
from app.decorators import teacher_required  # 你可以自定义角色验证装饰器
import os
import json
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import db
from app.models import StudentAnswerRecord
from app.models.CourseMaterial import CourseMaterial
from app.routes.student import parse_questions


from app.utils.ai_utils import generate_questions_with_ai  # 根据你AI函数所在位置调整路径

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")

@teacher_bp.route("/")
@login_required
@teacher_required
def teacher_home():
    return render_template("teacher_home.html")

@teacher_bp.route("/materials")
@login_required
@teacher_required
def view_all_uploads():
    materials = CourseMaterial.query.filter_by(is_standard=True).order_by(CourseMaterial.created_at.desc()).all()
    return render_template("teacher_materials.html", materials=materials)

@teacher_bp.route('/upload_standard', methods=['GET', 'POST'])
@login_required
def upload_standard_material():
    if request.method == 'POST':
        file = request.files['material']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join('uploads', filename)
            file.save(filepath)

            # # 调用 AI 接口生成题目
            # questions = generate_questions_with_ai(filepath)

            raw_text = generate_questions_with_ai(filepath)
            questions = parse_questions(raw_text)



            # 保存到数据库
            material = CourseMaterial(
                filename=filename,
                filepath=filepath,
                ai_generated_questions=json.dumps(questions, ensure_ascii=False),
                teacher_id=current_user.id,
                is_standard=True  # 关键标志
            )
            db.session.add(material)
            db.session.commit()

            flash("上传成功并已生成标准题库！", "success")
            # ✅ 上传成功后跳转到查看该资料作答记录页面

            redirect(url_for('teacher.teacher_home'))

    return render_template('teacher_upload_standard.html')

@teacher_bp.route('/material_records/<int:material_id>')
@login_required
def view_material_records(material_id):
    material = CourseMaterial.query.filter_by(id=material_id, is_standard=True).first_or_404()
    records = StudentAnswerRecord.query.filter_by(material_id=material_id).order_by(StudentAnswerRecord.student_id).all()
    return render_template('teacher_view_records.html', material=material, records=records)

# @teacher_bp.route('/material_stats/<int:material_id>')
# @login_required
# def material_stats(material_id):
#     material = CourseMaterial.query.get_or_404(material_id)
#
#     # 查找该标准资料的所有学生答题记录
#     records = StudentAnswerRecord.query.filter_by(material_id=material_id).all()
#
#     student_names = [record.student_name for record in records]
#     average_scores = [record.average_score for record in records]
#
#     return render_template('teacher_material_stats.html',
#                            material=material,
#                            student_names=student_names,
#                            average_scores=average_scores)

from collections import defaultdict

@teacher_bp.route('/material_stats/<int:material_id>')
@login_required
@teacher_required
def material_stats(material_id):
    material = CourseMaterial.query.get_or_404(material_id)

    # 查询该资料下的所有学生答题记录
    records = StudentAnswerRecord.query.filter_by(material_id=material_id).all()

    # 构造 学生名 → 分数字典
    score_dict = defaultdict(list)
    for record in records:
        if record.student:  # 安全判断
            score_dict[record.student.name].append(record.score)

    # 构造图表数据
    student_names = []
    average_scores = []
    for name, scores in score_dict.items():
        student_names.append(name)
        average_scores.append(round(sum(scores) / len(scores), 2))

    return render_template('teacher_material_stats.html',
                           material=material,
                           student_names=student_names,
                           average_scores=average_scores)

@teacher_bp.route('/edit_material/<int:material_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_material(material_id):
    material = CourseMaterial.query.filter_by(id=material_id, is_standard=True).first_or_404()

    if request.method == 'POST':
        # 获取所有题目数据
        updated_questions = []
        total = int(request.form.get('total_questions', 0))
        for i in range(1, total + 1):
            question_text = request.form.get(f'question_{i}', '')
            options = [request.form.get(f'option_{i}_{j}', '') for j in range(1, 5)]
            answer = request.form.get(f'answer_{i}', '')
            updated_questions.append({
                "question": question_text,
                "options": options,
                "answer": answer
            })

        # 存入数据库
        material.ai_generated_questions = json.dumps(updated_questions, ensure_ascii=False)
        db.session.commit()

        flash("题目已更新成功！", "success")
        return redirect(url_for('teacher.view_all_uploads', material_id=material.id))

    # GET 请求：加载原始题库
    try:
        questions = json.loads(material.ai_generated_questions or "[]")
    except Exception:
        questions = []

    return render_template('teacher_edit_material.html', material=material, questions=questions)

@teacher_bp.route('/student_progress', methods=['GET', 'POST'])
@login_required
@teacher_required
def student_progress():

    from collections import defaultdict
    import datetime

    # 获取所有学生（假设用角色区分）
    students = User.query.filter_by(role='Student').all()

    selected_student_id = request.form.get('student_id')
    chart_data = []

    if request.method == 'POST' and selected_student_id:
        from app.models.student_answer_record import StudentAnswerRecord

        # 获取该学生所有答题记录
        records = StudentAnswerRecord.query.filter_by(student_id=selected_student_id).order_by(StudentAnswerRecord.timestamp).all()

        # 分组计算每个时间点的平均得分
        date_scores = defaultdict(list)
        for r in records:
            date = r.timestamp.strftime('%Y-%m-%d')
            date_scores[date].append(r.score)

        # 构建图表数据（时间 → 平均分）
        for date in sorted(date_scores):
            avg = sum(date_scores[date]) / len(date_scores[date])
            chart_data.append((date, round(avg, 2)))

    return render_template('teacher_student_progress.html',
                           students=students,
                           chart_data=chart_data,
                           selected_student_id=selected_student_id)

@teacher_bp.route('/material_difficulty/<int:material_id>')
@login_required
@teacher_required
def material_difficulty(material_id):
    material = CourseMaterial.query.filter_by(id=material_id, is_standard=True).first_or_404()
    questions = json.loads(material.ai_generated_questions or "[]")

    # 查找该题库下所有答题记录
    from app.models.student_answer_record import StudentAnswerRecord
    records = StudentAnswerRecord.query.filter_by(material_id=material_id).all()

    # 每题内容 → 得分列表
    from collections import defaultdict
    score_map = defaultdict(list)
    for r in records:
        score_map[r.question.strip()].append(r.score)

    # 生成统计数据：[(题目序号, 题干前30字, 平均得分)]
    analysis_data = []
    for idx, q in enumerate(questions, start=1):
        q_text = q['question'].strip()
        scores = score_map.get(q_text, [])
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        preview = q_text[:30] + ("..." if len(q_text) > 30 else "")
        analysis_data.append((f"题目 {idx}", preview, avg_score))

    return render_template('teacher_material_difficulty.html',
                           material=material,
                           analysis_data=analysis_data)

@teacher_bp.route("/material_report/<int:material_id>")
@login_required
@teacher_required
def material_report(material_id):
    from app.models.student_answer_record import StudentAnswerRecord
    from app.utils.ai_utils import generate_teacher_feedback_summary

    material = CourseMaterial.query.get_or_404(material_id)
    records = StudentAnswerRecord.query.filter_by(material_id=material.id).all()

    if not records:
        return render_template("teacher_material_report.html", material=material, message="暂无答题记录")

    avg_score = round(sum([r.score for r in records]) / len(records), 2)
    best = max(records, key=lambda r: r.score)
    worst = min(records, key=lambda r: r.score)

    ai_feedback = generate_teacher_feedback_summary(records)

    return render_template("teacher_material_report.html",
                           material=material,
                           avg_score=avg_score,
                           best=best,
                           worst=worst,
                           ai_feedback=ai_feedback)
