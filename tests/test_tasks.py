import asyncio
from typing import NoReturn
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from fastapi_restful.tasks import repeat_every


# Fixtures:

@pytest.fixture(scope="module")
def seconds() -> float:
    return 0.01


@pytest.fixture(scope="module")
def max_repetitions() -> int:
    return 3


@pytest.fixture(scope="module")
def wait_first(seconds) -> float:
    return seconds


@pytest.fixture
def asyncio_sleep_spy(mocker: MockerFixture) -> MagicMock:
    return mocker.spy(asyncio, "sleep")


# Tests:

@pytest.mark.asyncio
async def test_repeat_every_with_sync_function_and_max_repetitions(
        seconds: float, max_repetitions: int, asyncio_sleep_spy: MagicMock, mocker: MockerFixture
):
    counter = 0

    @repeat_every(seconds=seconds, max_repetitions=max_repetitions)
    def increase_counter() -> None:
        nonlocal counter
        counter += 1

    await increase_counter()

    assert counter == max_repetitions
    asyncio_sleep_spy.assert_has_calls(max_repetitions * [mocker.call(seconds)], any_order=True)


@pytest.mark.asyncio
async def test_repeat_every_with_sync_function_max_repetitions_and_wait_first(
        seconds: float, max_repetitions: int, wait_first: float, asyncio_sleep_spy: MagicMock, mocker: MockerFixture
):
    counter = 0

    @repeat_every(seconds=seconds, max_repetitions=max_repetitions, wait_first=seconds)
    def increase_counter() -> None:
        nonlocal counter
        counter += 1

    await increase_counter()

    assert counter == max_repetitions
    asyncio_sleep_spy.assert_has_calls((max_repetitions + 1) * [mocker.call(seconds)], any_order=True)


@pytest.mark.asyncio
async def test_repeat_every_with_sync_function_and_raise_exceptions_false(
        seconds: float, max_repetitions: int, asyncio_sleep_spy: MagicMock
):
    @repeat_every(seconds=seconds, max_repetitions=max_repetitions)
    def raise_exc() -> NoReturn:
        raise ValueError("error")

    try:
        await raise_exc()
    except ValueError as e:
        pytest.fail(
            f"{test_repeat_every_with_sync_function_and_raise_exceptions_false.__name__} raised an exception: {e}"
        )


@pytest.mark.asyncio
async def test_repeat_every_with_sync_function_and_raise_exceptions_true(seconds: float):
    @repeat_every(seconds=seconds, raise_exceptions=True)
    def raise_exc() -> NoReturn:
        raise ValueError("error")

    with pytest.raises(ValueError):
        await raise_exc()


@pytest.mark.asyncio
async def test_repeat_every_with_async_function_and_max_repetitions(
        seconds: float, max_repetitions: int, asyncio_sleep_spy: MagicMock, mocker: MockerFixture
):
    counter = 0

    @repeat_every(seconds=seconds, max_repetitions=max_repetitions)
    async def increase_counter() -> None:
        nonlocal counter
        counter += 1

    await increase_counter()

    assert counter == max_repetitions
    asyncio_sleep_spy.assert_has_calls(max_repetitions * [mocker.call(seconds)], any_order=True)


@pytest.mark.asyncio
async def test_repeat_every_with_async_function_max_repetitions_and_wait_first(
        seconds: float, max_repetitions: int, asyncio_sleep_spy: MagicMock, mocker: MockerFixture
):
    counter = 0

    @repeat_every(seconds=seconds, max_repetitions=max_repetitions, wait_first=seconds)
    async def increase_counter() -> None:
        nonlocal counter
        counter += 1

    await increase_counter()

    assert counter == max_repetitions
    asyncio_sleep_spy.assert_has_calls((max_repetitions + 1) * [mocker.call(seconds)], any_order=True)


@pytest.mark.asyncio
async def test_repeat_every_with_async_function_and_raise_exceptions_false(seconds: float, max_repetitions: int):
    @repeat_every(seconds=seconds, max_repetitions=max_repetitions)
    async def raise_exc() -> NoReturn:
        raise ValueError("error")

    try:
        await raise_exc()
    except ValueError as e:
        pytest.fail(
            f"{test_repeat_every_with_async_function_and_raise_exceptions_false.__name__} raised an exception: {e}"
        )


@pytest.mark.asyncio
async def test_repeat_every_with_async_function_and_raise_exceptions_true(seconds: float):
    @repeat_every(seconds=seconds, raise_exceptions=True)
    async def raise_exc() -> NoReturn:
        raise ValueError("error")

    with pytest.raises(ValueError):
        await raise_exc()
