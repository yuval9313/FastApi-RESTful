import pytest
from typing import Any, Dict, List, Union

from fastapi import status, FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient

from fastapi_restful.cbv_base import Api, Resource, set_responses


class AbstractTest:
    @pytest.fixture(scope="class")
    def app(self):
        return FastAPI()

    @pytest.fixture(scope="class")
    def client(self, app):
        return TestClient(app)

    @pytest.fixture(scope="class")
    def api(self, app):
        return Api(app)

    @pytest.fixture
    def cbv_resource(self):
        pass


class TestCbv(AbstractTest):
    WANTED_ATTR ="cy"
    INPUTTED = 2
    BUILTIN = 1

    @pytest.fixture
    def cbv_resource(self):
        class CBV(Resource):
            def __init__(self, user_input: int = 1):
                super().__init__()
                self.builtin_value = TestCbv.BUILTIN
                self.configured_value = user_input

            @set_responses(int)
            def post(self, user_given: int) -> int:
                print(user_given)
                return user_given + self.builtin_value + self.configured_value

            @set_responses(bool)
            def get(self) -> bool:
                return hasattr(self, TestCbv.WANTED_ATTR)

        return CBV

    def setup_method(self):
        self.posted_value = 2

    @pytest.fixture(autouse=True)
    def add_resource(self, api: Api, cbv_resource: object):
        cbv = cbv_resource(self.INPUTTED)
        api.add_resource(cbv, "/", "/classvar")

    def test_post_params(self, client: TestClient):
        response_post = client.post("/", params={
                                    "user_given": self.posted_value}, json={})
        summed = self.posted_value + self.BUILTIN + self.INPUTTED
        assert response_post.status_code == status.HTTP_200_OK
        assert response_post.json() == summed

    def test_get_classvar(self, client: TestClient):
        response_2 = client.get("/classvar")
        assert response_2.status_code == status.HTTP_200_OK
        assert response_2.json() is False


class TestArgsInPath(AbstractTest):
    ITEM = "test"

    @pytest.fixture
    def cbv_resource(self):
        class TestCBV(Resource):
            @set_responses(str)
            def get(self, item_id: str) -> str:
                return item_id

        return TestCBV

    @staticmethod
    @pytest.fixture(autouse=True)
    def add_resource(cbv_resource: object, api: Api):
        resource = cbv_resource()
        api.add_resource(resource, "/{item_id}")

    def test_args(self, client: TestClient):
        assert client.get(f"/{self.ITEM}").json() == self.ITEM


class TestMultipleRoutes(AbstractTest):
    @pytest.fixture
    def cbv_resource(self):
        class RootHandler(Resource):
            def get(self, item_path: str = None) -> Union[List[Any],
                                                          Dict[str, str]]:
                if item_path:
                    return {"item_path": item_path}
                return []

        return RootHandler

    @pytest.fixture(autouse=True)
    def add_resource(self, cbv_resource: object, api: Api):
        root_handler_resource = cbv_resource()
        api.add_resource(root_handler_resource, "/items/?",
                         "/items/{item_path:path}")

    def test_routes(self, client):
        assert client.get("/items/1").json() == {"item_path": "1"}
        assert client.get("/items").json() == []


class TestDifferentResponseModule(AbstractTest):
    CHOSEN_ROUTE = "/check"
    RESPONSE = "Done!"

    @pytest.fixture
    def cbv_resource(self):
        class RootHandler(Resource):
            @set_responses({}, response_class=PlainTextResponse)
            def get(self) -> str:
                return TestDifferentResponseModule.RESPONSE

        return RootHandler

    @pytest.fixture(autouse=True)
    def add_resource(self, api: Api, cbv_resource: object):
        api.add_resource(cbv_resource(), self.CHOSEN_ROUTE)

    def test_different_response(self, client: TestClient):
        assert client.get(self.CHOSEN_ROUTE).text == self.RESPONSE
