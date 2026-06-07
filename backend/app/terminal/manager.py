import logging
import shutil

from app.terminal.host_runtime import HostRuntime
from app.terminal.runtime import Runtime

logger = logging.getLogger(__name__)


def _resolve_shell(shell: str) -> str:
    """Resolve shell name to full path."""
    if "/" in shell:
        return shell
    resolved = shutil.which(shell)
    if resolved:
        return resolved
    # Fallback: try common locations
    for path in [f"/bin/{shell}", f"/usr/bin/{shell}"]:
        import os
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    # Ultimate fallback
    return "/bin/sh"


class RuntimeManager:
    _instance: "RuntimeManager | None" = None
    _runtimes: dict[str, Runtime]

    def __new__(cls) -> "RuntimeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._runtimes = {}
        return cls._instance

    async def create_runtime(
        self,
        session_id: str,
        shell: str,
        cols: int,
        rows: int,
        cwd: str | None = None,
    ) -> Runtime:
        if session_id in self._runtimes:
            existing = self._runtimes[session_id]
            if existing.is_alive:
                raise RuntimeError(
                    f"Runtime for session '{session_id}' already exists and is alive"
                )
            # Clean up dead runtime
            await self.destroy_runtime(session_id)

        resolved_shell = _resolve_shell(shell)
        runtime = HostRuntime()
        await runtime.start(shell=resolved_shell, cols=cols, rows=rows, cwd=cwd)
        self._runtimes[session_id] = runtime
        logger.info("Created runtime for session '%s'", session_id)
        return runtime

    async def get_runtime(self, session_id: str) -> Runtime | None:
        return self._runtimes.get(session_id)

    async def destroy_runtime(self, session_id: str) -> None:
        runtime = self._runtimes.pop(session_id, None)
        if runtime is not None:
            await runtime.stop()
            logger.info("Destroyed runtime for session '%s'", session_id)

    async def get_all_runtimes(self) -> dict[str, Runtime]:
        return dict(self._runtimes)
