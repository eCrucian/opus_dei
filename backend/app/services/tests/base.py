from abc import ABC, abstractmethod
from datetime import datetime
from app.models.validation import TestResult, TestStatus
from app.services.llm.base import BaseLLMClient


class BaseTest(ABC):
    test_id: str
    test_name: str

    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    async def run(self, *args, **kwargs) -> TestResult:
        result = TestResult(test_id=self.test_id, test_name=self.test_name)
        result.started_at = datetime.utcnow()
        try:
            await self._execute(result, *args, **kwargs)
        except Exception as exc:
            result.status = TestStatus.FAILED
            result.summary = f"Erro interno: {exc}"
        result.finished_at = datetime.utcnow()
        return result

    @abstractmethod
    async def _execute(self, result: TestResult, *args, **kwargs) -> None:
        ...
