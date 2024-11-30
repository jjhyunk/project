from datetime import datetime
import json
import random
import secrets

from dotenv import load_dotenv
import os
from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from flask_migrate import Migrate
from flask_restx import Api, Resource
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from werkzeug.security import check_password_hash

from db_setup import db
from models import Message, Quipu, User
from flasgger import Swagger
from sqlalchemy import inspect, select

load_dotenv()

app = Flask(__name__)
# app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:1212@localhost/mywork"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# app.config["SERVER_NAME"] = "localhost:8080"
# app.config["SECRET_KEY"] = "your-secret-key"  # JWT 토큰 생성에 필요한 비밀 키

# SECRET_KEY = "my_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SERVER_NAME"] = os.getenv("SERVER_NAME")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

db.init_app(app)

migrate = Migrate(app, db)

api = Api(app, doc="/swagger")  # Flask 객체에 Api 객체 등록
swagger = Swagger(app, template_file="./swagger.json")
jwt = JWTManager(app)


def create_message_table(user_id):
    """유저별 메시지 테이블 동적 생성 함수."""
    table_name = f"messages_user_{user_id}"

    # 테이블이 이미 존재하면 그것을 return
    connection = db.engine.connect()
    if inspect(connection).has_table(table_name):
        return Table(table_name, db.metadata, autoload_with=db.engine)
    # 없으면 새로 생성
    table = Table(
        table_name,
        db.metadata,
        Column("memo_id", Integer, primary_key=True, autoincrement=True),
        Column("content", Text, nullable=False),
        Column("writer_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("choiceType", String(50), nullable=False),
        Column("created_at", DateTime, default=datetime.now()),
    )
    try:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        table.create(db.engine)
    except Exception as e:
        print(f"테이블 생성 중 오류 발생: {e}")
    finally:
        connection.close()

    return table


def create_message(user_id, content, writer_id, choice_type):
    # 테이블이 이미 생성되어 있으니 해당 테이블에 메시지 삽입
    table_name = f"messages_user_{user_id}"

    # 테이블 객체를 가져온다
    try:
        table = Table(table_name, db.metadata, autoload_with=db.engine)
    except Exception as e:
        return {"error": f"테이블을 로드하는데 실패했습니다: {str(e)}"}, 500

    # 동적으로 생성된 테이블에 메시지 삽입
    try:
        # 테이블에 데이터 삽입
        db.session.execute(
            table.insert().values(
                content=content,
                writer_id=writer_id,
                choiceType=choice_type,
                created_at=datetime.now()
            )
        )
        db.session.commit()

        return (
                {
                    "status": "success",
                    "message": "메시지가 성공적으로 작성되었습니다.",
                }
            ,
            201,
        )
    except Exception as e:
        # 오류 발생 시 롤백
        db.session.rollback()
        return {"error": f"메시지 작성 중 오류가 발생했습니다: {str(e)}"}, 500


@api.route("/register")
class Register(Resource):
    def post(self):
        data = request.get_json()

        name = data.get("name")
        studentID = data.get("studentID")
        password = data.get("password")
        choiceType = data.get("choiceType")
        topic = data.get("topic", None)

        if not name or not studentID or not password or not choiceType:
            return {"error": "모든 필수 값을 입력해주세요."}, 400

        # quipu 데이터베이스에서 studentID 확인
        quipu_student = Quipu.query.filter_by(studentID=studentID).first()
        if not quipu_student:
            return (
                    {"error": "해당 학번이 quipu 데이터베이스에 존재하지 않습니다."}
                ,
                400,
            )

        else:
            if User.query.filter_by(studentID=studentID).first():
                return {"error" : "이미 존재하는 학번입니다."},400
            new_user = User(
                username=name,
                studentID=studentID,
                choiceType=choiceType,
                topic=topic,
            )
            new_user.password = password
            new_user.set_nickname()
            try:
                db.session.add(new_user)
                db.session.commit()
                create_message_table(new_user.id)
                return {"message": "회원가입이 완료되었습니다."}, 201

            except Exception as e:
                db.session.rollback()
                return {"error": f"회원가입 중 오류가 발생했습니다: {str(e)}"}, 500


    def get(self):
        return {"error": "Methods Error"}, 405


@api.route("/register/quipuCheck")
class Check(Resource):
    def post(self):

        data = request.get_json()
        studentID = data.get("studentID")

        if not studentID:
            return {"error": "학번을 입력하세요."}, 400

        # 학번이 데이터베이스에 있는지 확인
        student = Quipu.query.filter_by(studentID=studentID).first()

        if student:
            return {"exists": True, "message": "학번이 존재합니다."}, 200
        else:
            return (
                {"exists": False, "message": "학번이 존재하지 않습니다."},
                404,
            )


@api.route("/login")
class Login(Resource):
    def post(self):
        data = request.get_json()

        studentID = data.get("studentID")
        password = data.get("password")

        if not studentID or not password:
            return {"error": "모든 필수 값을 입력해주세요."}, 400

        existing_user = User.query.filter_by(studentID=studentID).first()
        if not existing_user:
            return {"error": "가입되지 않은 회원입니다."}, 400

        if not existing_user.verify_password(password):
            return {"error": "비밀번호가 일치하지 않습니다."}, 400

        access_token = create_access_token(identity=existing_user.id)

        return (
                {
                    "status": "success",
                    "message": "로그인 성공",
                    "name": existing_user.username,
                    "choiceType": existing_user.choiceType,
                    "token": access_token,
                }
            ,
            200,
        )

    def get(self):
        return ({"error": "Methods Error"}, 405)


@api.route("/myStore/<int:userID>")
class MyStore(Resource):
    @jwt_required()
    def get(self, userID):

        # 현재 로그인한 사용자의 ID를 가져옴
        current_user_id = get_jwt_identity()
        print(current_user_id)
        # 로그인한 사용자의 ID와 요청된 userID가 일치하는지 확인
        if current_user_id != userID:
            return (
                    {
                        "status": "fail",
                        "message": "로그인한 사용자만 본인의 정보를 확인할 수 있습니다.",
                    }
                ,
                403,
            )

        user = User.query.filter_by(id=userID).first()

        if not user:
            return (
                    {
                        "status": "fail",
                        "message": f"User with ID {userID} not found.",
                        "data": None,
                    }
                ,
                404,
            )

        return (
                {
                    "status": "success",
                    "message": f"MyStore for userID {userID}",
                    "data": {
                        "username": user.username,
                        "choiceType": user.choiceType,
                    },
                }
            ,
            200,
        )


@api.route("/store/<int:userID>")
class Store(Resource):
    def get(self, userID):

        user = User.query.filter_by(id=userID).first()

        if not user:
            return (
                    {
                        "status": "fail",
                        "message": f"User with ID {userID} not found.",
                        "data": None,
                    }
                ,
                404,
            )

        return (
                {
                    "status": "success",
                    "message": f"Store for userID {userID}",
                    "data": {
                        "username": user.username,
                        "choiceType": user.choiceType,
                    },
                }
            ,
            200,
        )


# @api.route("/store/<int:userID>/select")
# class MyStoreSelect(Resource):
# def get(self, userID):
# return {"message": f"Select store for userID {userID}"}


@api.route("/store/<int:userID>/write/<string:type>")
class StoreWrite(Resource):
    @jwt_required()
    def post(self, userID, type):

        current_user_id = get_jwt_identity()

        data = request.get_json()
        content = data.get("content")
        if userID == current_user_id:
            return {"error" : "본인의 붕어빵에는 쪽지를 작성할 수 없습니다"},404
        if not content:
            return {"error": "내용을 입력하세요."}, 400

        # 유저별 메시지 테이블에 데이터 삽입
        try:
            user = db.session.get(User, userID)
            if not user:
                return {"error": "유저를 찾을 수 없습니다."}, 403

            # 유저별 메세지 테이블 유무 확인
            create_message_table(userID)

            # 동적으로 생성된 테이블에 메시지 추가
            result = create_message(userID, content, current_user_id, type)
            if result[1] != 201:
                return result  # 오류 메시지 반환

            # 새로운 메시지 ID 가져오기
            new_message_id = result[0].get("status")

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return (
                {"error": f"메시지 작성 중 오류가 발생했습니다: {str(e)}"},
                500,
            )

        return {
            "status": "success",
            "message": f"{type} 쪽지가 성공적으로 작성되었습니다.",
            "data": {
                "memo_id": new_message_id,
                "writer_id": current_user_id,
                "content": content,
                "choiceType": type,
            },
        }, 201


@api.route("/myStore/<int:userID>/read/<int:postID>")
class MyStoreRead(Resource):
    def get(self, userID, postID):
        #테이블 이름 동적 생성
        table_name = f"messages_user_{userID}"
        metadata = MetaData()

        try:
            table = Table(table_name, metadata, autoload_with=db.engine)
        except Exception as e:
            return (
                {"status": "error", "message": f"테이블 로드 실패: {str(e)}"},
                500,
            )        # 쪽지가 존재하지 않는 경우

        #쪽지 데이터 검색
        try:
            stmt = select(table).where(table.c.memo_id == postID)
            result = db.session.execute(stmt).fetchone()
            if not result:
                return (
                    {"status": "error", "message": "쪽지를 찾을 수 없습니다."},
                    404,
                )

            # 결과 반환
            return (
                {
                    "status": "success",
                    "data": {
                        "postID": result.memo_id,
                        "writer": result.writer_id,  # 테이블에 따라 수정 필요
                        "content": result.content,
                        "choiceType": result.choiceType,  # 테이블에 따라 수정 필요
                    },
                },
                200,
            )
        except Exception as e:
            return (
                {"status": "error", "message": f"데이터 검색 중 오류: {str(e)}"},
                500,
            )




@api.route("/allStore")
class AllStore(Resource):
    @jwt_required()
    def get(self):

        users = User.query.all()
        # 사용자가 없을 경우 처리
        if not users:
            return (
                {"status": "error", "message": "사용자가 없습니다."},
                404,
            )

        store_list = [{"userid": user.id, "username": user.username} for user in users]
        random_user = random.sample(users,2)
        return (
                {
                    "status": "success",
                    "data": {
                        "store_list": store_list,
                        "random_users": [
                            {"userid": user.id, "username": user.username}
                            for user in random_user
                        ],
                    },
                }
            ,
            200,
        )


def save_swagger_spec():
    with app.app_context():
        with open("swagger.json", "w") as f:
            json.dump(api.__schema__, f, indent=4)


if __name__ == "__main__":
    # save_swagger_spec()
    app.run(host="0.0.0.0", port=5000, debug=True)
