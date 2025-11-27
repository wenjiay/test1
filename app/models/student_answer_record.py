from app.models import db
from datetime import datetime

class StudentAnswerRecord(db.Model):
    __tablename__ = 'student_answer_record'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    material_id = db.Column(db.Integer, db.ForeignKey('course_material.id'))
    question = db.Column(db.Text)
    student_answer = db.Column(db.Text)
    score = db.Column(db.Integer)
    comment = db.Column(db.Text)
    recommendation = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ 新增：建立和 User 的关系
    student = db.relationship('User', backref='answer_records', foreign_keys=[student_id])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ 新增时间字段

    knowledge_tag = db.Column(db.String(100))  # 示例：'数学', '编程', '英语词汇'
