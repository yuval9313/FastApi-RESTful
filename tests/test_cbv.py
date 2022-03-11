from typing import Any, ClassVar

import pytest

from fastapi import status
from fastapi import APIRouter, Depends
from starlette.testclient import TestClient

from fastapi_restful.cbv import cbv


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
    FIRST = 1
    SECOND = 2

    @pytest.fixture(scope="class")
    def cbv_router(self, router: APIRouter):
        @cbv(router)
        class CBV:
            def __init__(self) -> None:
                self.first = TestResponseModels.FIRST
                self.second = TestResponseModels.SECOND

            @router.get("/", response_model=str)
            def string_response(self) -> str:
                return TestResponseModels.EXPECTED_RESPONSE

            @router.get("/sum", response_model=int)
            def int_response(self) -> int:
                return self.first + self.second

        return

    def test_str_response(self, cbv_router: None, client: TestClient) -> None:
        response_home = client.get("/")
        assert response_home.status_code == status.HTTP_200_OK
        assert response_home.json() == self.EXPECTED_RESPONSE

    def test_sum_response(self, cbv_router: None, client: TestClient):
        sum_response = client.get("/sum")
        assert sum_response.status_code == status.HTTP_200_OK
        assert sum_response.json() == self.FIRST + self.SECOND


class TestDependencies(AbstractTestRouter):
    FIRST = 3
    SECOND = 6

    @pytest.fixture(scope="class")
    def cbv_router(self, router: APIRouter):
        def dependency_one() -> int:
            return TestDependencies.FIRST

        def dependency_two() -> int:
            return TestDependencies.SECOND

        @cbv(router)
        class CBV:
            dataclass_defined_dependency: int = Depends(dependency_one)

            def __init__(self, two: int = Depends(dependency_two)):
                self.init_defined_dependency = two

            @router.get("/", response_model=int)
            def int_dependencies(self) -> int:
                return self.dataclass_defined_dependency + self.init_defined_dependency

        return

    def test_dependencies(self, cbv_router: None, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == self.FIRST + self.SECOND


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
        assert response.status_code == status.HTTP_200_OK
        assert not response.json()


class TestMultipleTests(AbstractTestRouter):
    custom_path = "abc"
    num_path = "1"

    @pytest.fixture(scope="class")
    def cbv_router(self, router: APIRouter):
        @cbv(router)
        class CBV:
            @router.get("/items")
            @router.get("/items/{custom_path:path}")
            @router.get("/database/{custom_path:path}")
            def root(self, custom_path: str = None) -> Any:
                return {"custom_path": custom_path} if custom_path else []

        return

    def test_get_items(self, cbv_router: None,  client: TestClient):
        items_response = client.get("/items")
        assert items_response.json() == []

    @pytest.mark.parametrize("param", [custom_path, num_path])
    def test_multiple_paths(self, cbv_router: None,
                            client: TestClient, param: str) -> None:
        specific_item_response = client.get(f"/database/{param}")
        assert specific_item_response.json() == {"custom_path": param}


class TestRequestQuery(AbstractTestRouter):
    def setup_method(self):
        self.param = 3

    @pytest.fixture(scope="class")
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
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == self.ITEM_RESPONSE
