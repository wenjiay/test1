
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.models.CourseMaterial import CourseMaterial
from app.models.student_answer_record import StudentAnswerRecord
from app.models import db
from app.utils.file_utils import extract_text_from_file
from app.utils.ai_utils import generate_questions_with_ai, evaluate_student_answers
import json
student_bp = Blueprint('student', __name__)


@student_bp.route("/")
@login_required
def student_home():
    return render_template("student_home.html")

@student_bp.route('/student/upload_material', methods=['GET', 'POST'])
@login_required
def upload_material():
    if current_user.role != 'Student':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        file = request.files['material']
        if file:
            filename = secure_filename(file.filename)

            # ✅ 使用 app.config 中统一配置的上传路径
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

            # 保存文件
            file.save(filepath)

            # 提取文本
            content = extract_text_from_file(filepath)

            # AI 生成题目
            questions = generate_questions_with_ai(content) if content else "无法识别文件内容。"

            # # 存入数据库
            # new_material = CourseMaterial(
            #     filename=filename,
            #     filepath=filepath,
            #     student_id=current_user.id,
            #     ai_generated_questions=questions
            # )
            # 解析原始题目串为结构化列表
            parsed_questions = parse_questions(questions)

            # 保存为 JSON 字符串（方便未来读取/打分）
            new_material = CourseMaterial(
                filename=filename,
                filepath=filepath,
                student_id=current_user.id,
                ai_generated_questions=json.dumps(parsed_questions, ensure_ascii=False)
            )

            db.session.add(new_material)
            db.session.commit()

            return redirect(url_for('student.view_material', material_id=new_material.id))

    return render_template('student_upload_material.html')



import re  # 开头确保有引入

def parse_questions(raw_text):
    raw_questions = re.split(r"(?:题目\d*[:：]|Question\s*\d*[:：])", raw_text)[1:]
    parsed = []
    for q in raw_questions:
        lines = q.strip().split("\n")
        question_text = []
        options = []
        answer = ""
        for line in lines:
            line = line.strip()
            if re.match(r"[A-Da-d][\.\、，：:]", line):  # 匹配 A. A、 A:
                options.append(line)
            elif "正确答案" in line or "答案" in line or "Answer" in line:
                answer = line
            else:
                question_text.append(line)
        parsed.append({
            "question": " ".join(question_text),
            "options": options,
            "answer": answer
        })
    return parsed

@student_bp.route("/view_material/<int:material_id>")
@login_required
def view_material(material_id):
    material = CourseMaterial.query.get_or_404(material_id)
    # parsed_questions = parse_questions(material.ai_generated_questions or "")
    # ✅ 改为直接加载 JSON 格式
    # import json
    # questions = json.loads(material.ai_generated_questions or "[]")
    # return render_template("view_material.html", material=material, questions=questions)
    try:
        questions = json.loads(material.ai_generated_questions or "[]")
    except Exception as e:
        questions = []
    return render_template("student_view_material.html", material=material, questions=questions)

from flask import send_file
from io import BytesIO

@student_bp.route('/download_material/<int:material_id>')
@login_required
def download_material(material_id):
    material = CourseMaterial.query.get_or_404(material_id)

    # 解析题目（和 view_material 用一样的逻辑）
    questions = json.loads(material.ai_generated_questions or "[]")

    # 构建文本内容
    output = ""
    for idx, q in enumerate(questions, start=1):
        output += f"题目 {idx}：{q['question']}\n"
        for opt in q['options']:
            output += f"{opt}\n"
        output += f"\n【答案】{q['answer']}\n\n"

    # 转为内存文件返回
    buffer = BytesIO()
    buffer.write(output.encode('utf-8'))
    buffer.seek(0)

    download_filename = material.filename.rsplit('.', 1)[0] + "_题目.txt"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=download_filename,
        mimetype='text/plain'
    )

@student_bp.route("/materials")
@login_required
def view_all_materials():
    materials = CourseMaterial.query.filter_by(student_id=current_user.id).order_by(CourseMaterial.created_at.desc()).all()
    return render_template("student_materials.html", materials=materials)

@student_bp.route('/submit_answers/<int:material_id>', methods=['POST'])
@login_required
def submit_answers(material_id):
    material = CourseMaterial.query.get_or_404(material_id)

    # # 从 material 中获取题目列表（原始 JSON）
    # questions = material.generated_questions
    # if isinstance(questions, str):
    #     questions = json.loads(questions)
    # 从 material 中获取题目列表（原始 JSON）
    questions = json.loads(material.ai_generated_questions or "[]")  # ✅ 字段名改成 ai_generated_questions

    # 收集所有答案
    answers = []
    for idx in range(1, len(questions) + 1):
        answer = request.form.get(f'answer_{idx}', '')
        answers.append(answer)

    # 调用 AI 模块打分与点评
    feedback = evaluate_student_answers(questions, answers)
    # feedback: {'scores': [...], 'comments': [...], 'recommendations': [...]}

    # ✅ 保存记录到数据库
    for i, q in enumerate(questions):
        record = StudentAnswerRecord(
            student_id=current_user.id,
            material_id=material.id,
            question=q["question"],
            student_answer=answers[i],
            score=feedback["scores"][i],
            comment=feedback["comments"][i],
            recommendation=feedback["recommendations"][i]
        )


    db.session.commit()

    # return render_template('student_answer_result.html',
    #                        questions=questions,
    #                        answers=answers,
    #                        scores=feedback['scores'],
    #                        comments=feedback['comments'],
    #                        recommendations=feedback['recommendations'])
    # ✅ 提前打包 zip，用于模板循环
    zipped_result = zip(questions, answers, feedback['scores'], feedback['comments'], feedback['recommendations'])

    # ✅ 渲染模板时传入 zipped_result
    return render_template('student_answer_result.html',
                           zipped_result=zipped_result,
                           material=material)  # 如果你还想在模板中显示上传文件名

@student_bp.route('/standard_list')
@login_required
def standard_material_list():
    materials = CourseMaterial.query.filter_by(is_standard=True).order_by(CourseMaterial.created_at.desc()).all()
    return render_template('student_standard_list.html', materials=materials)

@student_bp.route('/answer_standard/<int:material_id>', methods=['GET', 'POST'])
@login_required
def answer_standard(material_id):
    material = CourseMaterial.query.filter_by(id=material_id, is_standard=True).first_or_404()
    questions = json.loads(material.ai_generated_questions or "[]")

    if request.method == 'POST':
        answers = [request.form.get(f'answer_{i+1}', '') for i in range(len(questions))]

        feedback = evaluate_student_answers(questions, answers)

        # 保存答题记录
        for i, q in enumerate(questions):
            record = StudentAnswerRecord(
                student_id=current_user.id,
                material_id=material.id,
                question=q["question"],
                student_answer=answers[i],
                score=feedback["scores"][i],
                comment=feedback["comments"][i],
                recommendation=feedback["recommendations"][i]
            )
            db.session.add(record)

        db.session.commit()

        zipped_result = zip(questions, answers, feedback["scores"], feedback["comments"], feedback["recommendations"])
        return render_template("student_answer_result.html", zipped_result=zipped_result, material=material)

    return render_template("student_answer_standard.html", questions=questions, material=material)

@student_bp.route("/chat_material/<int:material_id>", methods=["GET", "POST"])
@login_required
def chat_material(material_id):
    material = CourseMaterial.query.get_or_404(material_id)
    content = extract_text_from_file(material.filepath)
    answer = None
    user_question = None

    if request.method == "POST":
        user_question = request.form.get("question", "")
        from app.utils.ai_utils import chat_about_material
        answer = chat_about_material(content, user_question)

    return render_template("student_chat_material.html",
                           material=material,
                           question=user_question,
                           answer=answer)

@student_bp.route('/learning_path')
@login_required
def learning_path():
    from app.models.student_answer_record import StudentAnswerRecord
    from app.utils.ai_utils import recommend_learning_path

    records = StudentAnswerRecord.query.filter_by(student_id=current_user.id).order_by(StudentAnswerRecord.created_at.desc()).limit(20).all()

    if not records:
        return render_template("student_learning_path.html", path=None, message="你还没有答题记录，暂无法生成学习路径。")

    path = recommend_learning_path(records)
    return render_template("student_learning_path.html", path=path)

@student_bp.route("/material_summary/<int:material_id>")
@login_required
def material_summary(material_id):
    from app.utils.ai_utils import generate_summary_sheet
    material = CourseMaterial.query.get_or_404(material_id)
    content = extract_text_from_file(material.filepath)

    if not content:
        return render_template("student_summary.html", summary="❌ 无法提取资料内容。请确认上传的是PDF或PPT。", material=material)

    summary = generate_summary_sheet(content)
    return render_template("student_summary.html", summary=summary, material=material)

@student_bp.route("/radar_chart")
@login_required
def radar_chart():
    from app.models.student_answer_record import StudentAnswerRecord
    import matplotlib.pyplot as plt
    import numpy as np
    from io import BytesIO
    import base64

    records = StudentAnswerRecord.query.filter_by(student_id=current_user.id).all()

    tag_scores = {}
    tag_counts = {}

    for r in records:
        tag = getattr(r, 'knowledge_tag', None)
        if tag:
            tag_scores[tag] = tag_scores.get(tag, 0) + r.score
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    labels = list(tag_scores.keys())
    scores = [round(tag_scores[tag] / tag_counts[tag] * 10, 2) for tag in labels]  # 统一为 0~100 分

    # 画雷达图
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    scores += scores[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, scores, 'o-', linewidth=2)
    ax.fill(angles, scores, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles), labels + [labels[0]])
    ax.set_title("知识点掌握雷达图", size=15)
    ax.set_ylim(0, 100)

    # 转为 base64 图像
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    return render_template("student_radar_chart.html", chart_data=image_base64)
