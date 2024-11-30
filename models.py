from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from db_setup import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False)
    studentID = db.Column(db.String(20), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(50), nullable=False)
    choiceType = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<User {self.username}>"

    @property
    def password(self):
        raise AttributeError("읽어 들일 수 없음")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_nickname(self):
        """
        username에서 성을 제외한 나머지 이름 + '붕'을 붙여 nickname에 저장합니다.
        예: '홍길동' -> '길동붕'
        """
        # 이름 분리
        name_parts = self.username.split()
        if len(name_parts) > 1:
            # 성을 제외한 나머지 이름
            self.nickname = "".join(name_parts[1:]) + "붕"
        else:
            # 이름 전체 + '붕'
            self.nickname = self.username + "붕"


class Message(db.Model):
    __tablename__ = "messages"

    memo_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    writer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    choiceType = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    writer = db.relationship(
        "User", backref=db.backref("messages", lazy=True)
    )  # writer 관계 추가

    def __repr__(self):
        return f"<Message {self.memo_id}>"


# Quipu 회원 데이터베이스
class Quipu(db.Model):
    __tablename__ = "quipu_students"
    id = db.Column(db.Integer, primary_key=True)
    studentID = db.Column(db.String(20), unique=True, nullable=False)
