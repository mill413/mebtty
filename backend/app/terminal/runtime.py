from abc import ABC, abstractmethod
from typing import AsyncIterator


class Runtime(ABC):
    @abstractmethod
    async def start(
        self,
        shell: str,
        cols: int = 80,
        rows: int = 24,
        cwd: str | None = None,
        env: dict | None = None,
    ) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def write(self, data: bytes) -> None: ...

    @abstractmethod
    async def resize(self, cols: int, rows: int) -> None: ...

    @abstractmethod
    async def read(self) -> AsyncIterator[bytes]: ...

    @abstractmethod
    def current_cwd(self) -> str | None: ...

    def current_username(self) -> str | None:
        return None

    def current_process_name(self) -> str | None:
        return None

    @property
    @abstractmethod
    def is_alive(self) -> bool: ...
