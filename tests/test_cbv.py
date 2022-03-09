from typing import Any, ClassVar

import pytest
from fastapi import APIRouter, Depends
from starlette.testclient import TestClient

from fastapi_restful.cbv import cbv

ONE = 1
TWO = 2
THREE_AS_BYTES = b'3'
SUCCESS_CODE = 200


class AbstractTestRouter:
    @pytest.fixture(autouse=True, scope="module")
    def router(self) -> APIRouter:
        return APIRouter()

    @pytest.fixture(scope="function")
    def client(self, router: APIRouter):
        client = TestClient(router)
        return client

    @pytest.fixture(scope="class")
    def cbv_router(self, router: APIRouter):
        return


class TestResponseModels(AbstractTestRouter):
    EXPECTED_RESPONSE = "home"

    @pytest.fixture(scope="class")
    def cbv_router(self, router: APIRouter):
        @cbv(router)
        class CBV:
            def __init__(self) -> None:
                self.one = ONE
                self.two = TWO

            @router.get("/", response_model=str)
            def string_response(self) -> str:
                return TestResponseModels.EXPECTED_RESPONSE

            @router.get("/sum", response_model=int)
            def int_response(self) -> int:
                return self.one + self.two

        return

    def test_response_models(self, cbv_router: None,
                             client: TestClient) -> None:
        response_home = client.get("/")
        assert response_home.status_code == SUCCESS_CODE
        assert response_home.json() == self.EXPECTED_RESPONSE

        sum_response = client.get("/sum")
        assert sum_response.status_code == SUCCESS_CODE
        assert sum_response.content == THREE_AS_BYTES


class TestDependencies(AbstractTestRouter):
    @pytest.fixture(scope="class")
    def cbv_router(self, router: APIRouter):
        def dependency_one() -> int:
            return ONE

        def dependency_two() -> int:
            return TWO

        @cbv(router)
        class CBV:
            one: int = Depends(dependency_one)

            def __init__(self, two: int = Depends(dependency_two)):
                self.two = two

            @router.get("/", response_model=int)
            def int_dependencies(self) -> int:
                return self.one + self.two

        return

    def test_dependencies(self, cbv_router: None, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == SUCCESS_CODE
        assert response.content == THREE_AS_BYTES


class TestPathOrderPreservation(AbstractTestRouter):
    TEST_RESPONSE = 1
    OTHER_PATH_RESPONSE = 2

    @pytest.fixture(scope="class")
    def cbv_router(self, router: APIRouter):
        @cbv(router)
        class CBV:
            @router.get("/test")
            def get_test(self) -> int:
                return TestPathOrderPreservation.TEST_RESPONSE

            @router.get("/{any_path}")
            def get_any_path(self) -> int:  # Alphabetically before `get_test`.
                return TestPathOrderPreservation.OTHER_PATH_RESPONSE

    def test_routes_path_order_preserved(self, cbv_router: None,
                                         client: TestClient) -> None:
        assert client.get("/test").json() == self.TEST_RESPONSE
        assert client.get("/any_other_path").json() == self.OTHER_PATH_RESPONSE


class TestClassVar(AbstractTestRouter):
    @pytest.fixture(scope="function")
    def cbv_router(self, router: APIRouter):
        @cbv(router)
        class CBV:
            class_var: ClassVar[int]

            @router.get("/", response_model=bool)
            def g(self) -> bool:
                return hasattr(self, "class_var")

        return

    def test_class_var(self, cbv_router: None, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == SUCCESS_CODE
        assert response.content == b"false"


class TestMultipleTests(AbstractTestRouter):
    def setup_method(self):
        self.item = "abc"
        self.num_item = "1"

    @pytest.fixture(scope="function")
    def cbv_router(self, router: APIRouter):
        @cbv(router)
        class CBV:
            @router.get("/items")
            @router.get("/items/{custom_path:path}")
            @router.get("/database/{custom_path:path}")
            def root(self, custom_path: str = None) -> Any:
                return {"custom_path": custom_path} if custom_path else []

        return

    def test_multiple_paths(self, cbv_router: None,
                            client: TestClient) -> None:
        items_response = client.get("/items")
        assert items_response.json() == []

        specific_item_response = client.get(f"/database/{self.item}")
        assert specific_item_response.json() == {"custom_path": self.item}

        num_item_response = client.get(f"/items/{self.num_item}")
        assert num_item_response.json() == {"custom_path": self.num_item}


class TestRequestQuery(AbstractTestRouter):
    def setup_method(self):
        self.param = 3

    @pytest.fixture(scope="function")
    def cbv_router(self, router: APIRouter):
        @cbv(router)
        class CBV:
            @router.get("/route")
            def root(self, param: int = None) -> int:
                return param if param else 0

        return

    def test_query_parameters(self, cbv_router: None,
                              client: TestClient) -> None:
        assert client.get("/route").json() == 0
        assert client.get(f"/route?param={self.param}").json() == self.param


class TestPrefix(AbstractTestRouter):
    ITEM_RESPONSE = "hello"

    @pytest.fixture(scope="class", autouse=True)
    def router(self) -> APIRouter:
        return APIRouter(prefix="/api")

    @pytest.fixture(scope="class")
    def cbv_router(self, router: APIRouter):
        @cbv(router)
        class CBV:
            @router.get("/item")
            def root(self) -> str:
                return TestPrefix.ITEM_RESPONSE

    def test_prefix(self, cbv_router: None, client: TestClient):
        response = client.get("/api/item")
        assert response.status_code == SUCCESS_CODE
        assert response.json() == self.ITEM_RESPONSE
