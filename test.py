import json

from flask_restx import Api, Resource  # Api 구현을 위한 Api 객체 import

from flask import Flask, request  # 서버 구현을 위한 Flask 객체 import

app = Flask(
    __name__
)  # Flask 객체 선언, 파라미터로 어플리케이션 패키지의 이름을 넣어줌.
app.config["SERVER_NAME"] = "locahost:8080"

api = Api(app, doc="/swagger")  # Flask 객체에 Api 객체 등록


@api.route("/register")
class Register(Resource):
    def get(self):
        return {"message": "Login endpoint"}


@api.route("/login")
class Login(Resource):
    def get(self):
        return {"message": "Login endpoint"}


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
