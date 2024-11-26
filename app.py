import datetime
import json

from dotenv import load_dotenv
from flask import Flask, request
from flask_migrate import Migrate
from flask_restx import Api, Resource
from werkzeug.security import check_password_hash

from db_setup import db
from models import Message, User

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:1212@localhost/mywork"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SERVER_NAME"] = "localhost:8080"
# app.config["SECRET_KEY"] = "your-secret-key"  # JWT 토큰 생성에 필요한 비밀 키


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
            return {"error": "모든 필수 값을 입력해주세요."}, 400

        existing_user = User.query.filter_by(studentID=studentID).first()
        if existing_user:
            return {"error": "이미 등록된 학번입니다."}, 400

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
            return {"error": f"회원가입 중 오류가 발생했습니다: {str(e)}"}, 500

        return {"message": "회원가입이 완료되었습니다."}, 201


@api.route("/login")
class Login(Resource):
    def post(self):
        data = request.get_json()

        studentID = (data.get("studetnID"),)
        password = data.get("password")

        if not studentID or not password:
            return {"error": "모든 필수 값을 입력해주세요."}, 400

        existing_user = User.query.filter_by(studentID=studentID).first()

        if not existing_user:
            return {"error": "가입되지 않은 회원입니다."}, 400

        if not check_password_hash(existing_user.password, password):
            return {"error": "비밀번호가 일치하지 않습니다."}, 400

        # JWT 토큰 생성
        """token = jwt.encode(
            {"user_id": existing_user.id, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
            app.config["SECRET_KEY"],
            algorithm="HS256"
        )"""

        return {
            "status": "success",
            "message": "로그인 성공",
            "name": existing_user.username,
            "choiceType": existing_user.choiceType,
        }, 200


@api.route("/myStore/<int:userID>")
class MyStore(Resource):
    def get(self, userID):
        return {"message": f"MyStore for userID {userID}"}


@api.route("/myStore/<int:userID>/select")
class MyStoreSelect(Resource):
    def get(self, userID):
        return {"message": f"Select store for userID {userID}"}


@api.route("/myStore/<int:userID>/write/<string:type>")
class MyStoreWrite(Resource):
    def post(self, userID, type):
        return {"message": f"Write {type} for userID {userID}"}


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
