"""Tests for BaseTest — run(), timestamp injection, and error handling."""
import pytest
from datetime import datetime
from app.models.validation import TestResult, TestStatus
from app.services.tests.base import BaseTest
from app.services.llm.base import BaseLLMClient
from unittest.mock import MagicMock


class ConcreteTest(BaseTest):
    test_id = "T_concrete"
    test_name = "Concrete Test"

    async def _execute(self, result: TestResult, should_fail: bool = False) -> None:
        if should_fail:
            raise RuntimeError("expected failure")
        result.status = TestStatus.PASSED
        result.summary = "All good."


class TestBaseTestRun:
    async def test_run_sets_started_and_finished_at(self):
        llm = MagicMock(spec=BaseLLMClient)
        test = ConcreteTest(llm)
        result = await test.run()
        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.finished_at >= result.started_at

    async def test_run_calls_execute(self):
        llm = MagicMock(spec=BaseLLMClient)
        test = ConcreteTest(llm)
        result = await test.run()
        assert result.status == TestStatus.PASSED
        assert result.summary == "All good."

    async def test_run_sets_failed_on_exception(self):
        llm = MagicMock(spec=BaseLLMClient)
        test = ConcreteTest(llm)
        result = await test.run(should_fail=True)
        assert result.status == TestStatus.FAILED
        assert "expected failure" in result.summary

    async def test_run_still_sets_finished_at_on_error(self):
        llm = MagicMock(spec=BaseLLMClient)
        test = ConcreteTest(llm)
        result = await test.run(should_fail=True)
        assert result.finished_at is not None

    async def test_run_returns_test_result(self):
        llm = MagicMock(spec=BaseLLMClient)
        test = ConcreteTest(llm)
        result = await test.run()
        assert isinstance(result, TestResult)
        assert result.test_id == "T_concrete"
        assert result.test_name == "Concrete Test"

    async def test_run_passes_args_to_execute(self):
        class ArgCapturingTest(BaseTest):
            test_id = "T_args"
            test_name = "Args Test"
            captured = None

            async def _execute(self, result, *args, **kwargs):
                ArgCapturingTest.captured = (args, kwargs)
                result.status = TestStatus.PASSED

        llm = MagicMock(spec=BaseLLMClient)
        test = ArgCapturingTest(llm)
        await test.run("pos_arg", key="kw_arg")
        assert ArgCapturingTest.captured == (("pos_arg",), {"key": "kw_arg"})
