import datetime
import json
import secrets

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from flask_migrate import Migrate
from flask_restx import Api, Resource
from werkzeug.security import check_password_hash

from db_setup import db
from models import Message, Quipu, User

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:1212@localhost/mywork"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SERVER_NAME"] = "localhost:8080"
# app.config["SECRET_KEY"] = "your-secret-key"  # JWT 토큰 생성에 필요한 비밀 키

SECRET_KEY = "my_secret_key"

db.init_app(app)

migrate = Migrate(app, db)


api = Api(app, doc="/swagger")  # Flask 객체에 Api 객체 등록


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
            return jsonify({"error": "모든 필수 값을 입력해주세요."}), 400

        # quipu 데이터베이스에서 studentID 확인
        quipu_student = Quipu.query.filter_by(studentID=studentID).first()
        if not quipu_student:
            return (
                jsonify(
                    {"error": "해당 학번이 quipu 데이터베이스에 존재하지 않습니다."}
                ),
                400,
            )

        existing_user = User.query.filter_by(studentID=studentID).first()
        if existing_user:
            return jsonify({"error": "이미 등록된 학번입니다."}), 400

        new_user = User(
            username=name,
            studentID=studentID,
            password=password,
            choiceType=choiceType,
            topic=topic,
        )

        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"회원가입 중 오류가 발생했습니다: {str(e)}"}), 500

        return jsonify({"message": "회원가입이 완료되었습니다."}), 201

    def get(self):
        return jsonify({"error": "Methods Error"}), 405


@api.route("/register/quipuCheck")
class Check(Resource):
    def post(self):
        # 프론트엔드에서 전달된 JSON 데이터 읽기
        data = request.get_json()
        studentID = data.get("studentID")

        if not studentID:
            return jsonify({"error": "학번을 입력하세요."}), 400

        # 학번이 데이터베이스에 있는지 확인
        student = Quipu.query.filter_by(studentID=studentID).first()

        if student:
            return jsonify({"exists": True, "message": "학번이 존재합니다."}), 200
        else:
            return (
                jsonify({"exists": False, "message": "학번이 존재하지 않습니다."}),
                404,
            )


@api.route("/login")
class Login(Resource):
    def post(self):
        data = request.get_json()

        studentID = data.get("studetnID")
        password = data.get("password")

        if not studentID or not password:
            return jsonify({"error": "모든 필수 값을 입력해주세요."}), 400

        existing_user = User.query.filter_by(studentID=studentID).first()

        if not existing_user:
            return jsonify({"error": "가입되지 않은 회원입니다."}), 400

        if not check_password_hash(existing_user.password, password):
            return jsonify({"error": "비밀번호가 일치하지 않습니다."}), 400

        access_token = create_access_token(identity=User.id)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "로그인 성공",
                    "name": existing_user.username,
                    "choiceType": existing_user.choiceType,
                    "token": access_token,
                }
            ),
            200,
        )

    def get(self):
        return (jsonify({"error": "Methods Error"}), 405)


@api.route("/myStore/<int:userID>")
class MyStore(Resource):
    @jwt_required()
    def get(self, userID):

        # 현재 로그인한 사용자의 ID를 가져옴
        current_user_id = get_jwt_identity()

        # 로그인한 사용자의 ID와 요청된 userID가 일치하는지 확인
        if current_user_id != userID:
            return (
                jsonify(
                    {
                        "status": "fail",
                        "message": "로그인한 사용자만 본인의 정보를 확인할 수 있습니다.",
                    }
                ),
                403,
            )

        user = User.query.filter_by(id=userID).first()

        if not user:
            return (
                jsonify(
                    {
                        "status": "fail",
                        "message": f"User with ID {userID} not found.",
                        "data": None,
                    }
                ),
                404,
            )

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"MyStore for userID {userID}",
                    "data": {
                        "username": user.username,
                        "choiceType": user.choiceType,
                    },
                }
            ),
            200,
        )


# @api.route("/store/<int:userID>/select")
# class MyStoreSelect(Resource):
# def get(self, userID):
# return {"message": f"Select store for userID {userID}"}


@api.route("/store/<int:userID>/write/<string:type>")
class MyStoreWrite(Resource):
    def post(self, userID, type):

        data = request.get_json()
        content = data.get("content")

        # 데이터베이스에서 userID에 해당하는 사용자 가져오기
        try:
            user = User.query.filter_by(id=userID).first()
            if not user:
                return {
                    "status": "error",
                    "message": "해당 사용자 정보를 찾을 수 없습니다.",
                }, 404

            # 작성자 ID를 User 테이블에서 가져옴
            writer_id = user.studentID

        except Exception as e:
            return {
                "status": "error",
                "message": f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}",
            }, 500

        # 내용 확인
        if not content:
            return {
                "status": "error",
                "message": "내용을 입력해주세요.",
            }, 400

        # 성공 응답
        return {
            "message": f"Write {type} for userID {writer_id}",
            "writer_id": writer_id,
        }, 200


@api.route("/myStore/<int:userID>/read/<string:postID>")
class MyStoreRead(Resource):
    def get(self, userID, postID):
        return {"message": f"Read post {postID} for userID {userID}"}


@api.route("/allStore")
class AllStore(Resource):
    def get(self):
        return {"message": "All stores"}


@api.route("/hello")  # 데코레이터 이용, '/hello' 경로에 클래스 등록
class HelloWorld(Resource):
    def get(self):  # GET 요청시 리턴 값에 해당 하는 dict를 JSON 형태로 반환
        return {"message": "Hello, World!"}, 200


def save_swagger_spec():
    with app.app_context():
        with open("swagger.json", "w") as f:
            json.dump(api.__schema__, f, indent=4)


if __name__ == "__main__":
    save_swagger_spec()
    app.run(host="127.0.0.1", port=8080, debug=True)
