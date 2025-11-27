from .base import db
from datetime import datetime
class CourseMaterial(db.Model):
    __tablename__ = 'course_material'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    filepath = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=db.func.now())
    ai_generated_questions = db.Column(db.Text)

    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    student = db.relationship('User', backref='materials', foreign_keys=[student_id])
    is_standard = db.Column(db.Boolean, default=False)  # 教师上传的标准题库

    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    teacher = db.relationship('User', backref='uploaded_materials', foreign_keys=[teacher_id])
