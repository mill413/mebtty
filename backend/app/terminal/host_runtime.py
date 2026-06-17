import asyncio
import fcntl
import getpass
import logging
import os
import pwd
import pty
import signal
import struct

import termios
from typing import AsyncIterator

from app.terminal.runtime import Runtime

logger = logging.getLogger(__name__)


class HostRuntime(Runtime):
    def __init__(self) -> None:
        self._master_fd: int | None = None
        self._pid: int | None = None
        self._alive: bool = False
        self._read_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._read_task: asyncio.Task | None = None

    async def start(
        self,
        shell: str,
        cols: int = 80,
        rows: int = 24,
        cwd: str | None = None,
        env: dict | None = None,
    ) -> None:
        if self._alive:
            raise RuntimeError("Runtime is already running")

        # Build environment for the shell
        try:
            username = getpass.getuser()
        except Exception:
            username = os.environ.get("USER", "user")
        home = os.environ.get("HOME", pwd.getpwuid(os.getuid()).pw_dir)

        child_env = os.environ.copy()
        child_env.update({
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            # yazi uses this to select iTerm's inline image protocol,
            # which is supported by xterm-addon-image in the browser.
            "TERM_PROGRAM": "iTerm.app",
            "TERM_PROGRAM_VERSION": "3.5",
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "HOME": home,
            "USER": username,
            "LOGNAME": username,
            "SHELL": shell,
        })

        # Fix zsh fpath for oh-my-zsh compatibility.
        #
        # Remove FPATH from the child environment.  When FPATH is explicitly
        # set, zsh uses ONLY those paths and skips its compiled-in defaults
        # (e.g. /usr/share/zsh/functions/Misc, Completion/*, etc.).
        # The parent process may inherit FPATH from a zsh shell (e.g.
        # uvicorn running inside a zsh sandbox), so we strip it here.
        # With FPATH unset, zsh auto-populates fpath with all its built-in
        # system function paths, and oh-my-zsh prepends its own paths.
        child_env.pop("FPATH", None)

        # Disable oh-my-zsh's compfix security check.
        #
        # oh-my-zsh calls `compinit -i` which invokes `compaudit` to verify
        # directory ownership/permissions.  In sandboxed or containerized
        # environments, system zsh directories (e.g. /usr/share/zsh/) are
        # often owned by `nobody` rather than root, causing compaudit to
        # flag them as "insecure".  compinit then filters those directories
        # OUT of fpath, which breaks:
        #   - `autoload -U colors && colors` (needed by themes)
        #   - `compdump: function definition file not found`
        # Setting ZSH_DISABLE_COMPFIX=true makes oh-my-zsh call
        # `compinit -u` instead, which skips the security check and
        # preserves all fpath entries.
        if shell.endswith("/zsh"):
            child_env["ZSH_DISABLE_COMPFIX"] = "true"

        if env:
            child_env.update(env)

        effective_cwd = cwd if cwd and os.path.isdir(cwd) else home

        pid, master_fd = pty.fork()

        if pid == 0:
            # Child process
            os.chdir(effective_cwd)
            # Start as login shell: argv[0] prefixed with '-'
            login_name = "-" + os.path.basename(shell)
            os.execve(shell, [login_name], child_env)

        # Parent process
        self._pid = pid
        self._master_fd = master_fd
        self._alive = True

        # Set initial window size
        self._set_winsize(cols, rows)

        # Start async read loop using asyncio event-driven I/O
        self._read_task = asyncio.create_task(self._read_loop())

        logger.info(
            "HostRuntime started: pid=%d, fd=%d, shell=%s",
            self._pid,
            self._master_fd,
            shell,
        )

    async def stop(self) -> None:
        if not self._alive:
            return

        self._alive = False

        # Remove fd reader from event loop
        if self._master_fd is not None:
            try:
                loop = asyncio.get_event_loop()
                loop.remove_reader(self._master_fd)
            except Exception:
                pass

        # Cancel read task
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        # Signal the process
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

            # Give it a moment to terminate gracefully
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: os.waitpid(self._pid, os.WNOHANG)
                )
            except ChildProcessError:
                pass

            # Force kill if still alive
            try:
                os.kill(self._pid, signal.SIGKILL)
                os.waitpid(self._pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass

        # Close the file descriptor
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

        logger.info("HostRuntime stopped: pid=%s", self._pid)
        self._pid = None

    async def write(self, data: bytes) -> None:
        if self._master_fd is None:
            raise RuntimeError("Runtime is not running")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: os.write(self._master_fd, data))

    async def resize(self, cols: int, rows: int) -> None:
        if self._master_fd is None:
            raise RuntimeError("Runtime is not running")
        self._set_winsize(cols, rows)

    async def read(self) -> AsyncIterator[bytes]:
        while self._alive or not self._read_queue.empty():
            try:
                data = await asyncio.wait_for(self._read_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if data is None:
                break
            yield data

    def current_cwd(self) -> str | None:
        if self._pid is None:
            return None
        try:
            return os.readlink(f"/proc/{self._pid}/cwd")
        except OSError:
            return None

    @property
    def is_alive(self) -> bool:
        if not self._alive or self._pid is None:
            return False
        try:
            pid, status = os.waitpid(self._pid, os.WNOHANG)
            if pid != 0:
                self._alive = False
                return False
            return True
        except ChildProcessError:
            self._alive = False
            return False

    def _set_winsize(self, cols: int, rows: int) -> None:
        if self._master_fd is None:
            return
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)

    async def _read_loop(self) -> None:
        """Event-driven read loop using asyncio add_reader."""
        loop = asyncio.get_event_loop()
        fd = self._master_fd

        if fd is None:
            return

        async def _finish():
            await self._read_queue.put(None)
            self._alive = False

        def _on_readable():
            if not self._alive or self._master_fd is None:
                return
            try:
                # Read in a loop to drain all available data (edge-triggered style)
                while True:
                    data = os.read(self._master_fd, 65536)
                    if not data:
                        asyncio.ensure_future(_finish())
                        return
                    self._read_queue.put_nowait(data)
            except OSError as e:
                if e.errno in (5, 11):  # EIO or EAGAIN
                    if e.errno == 5:
                        logger.debug("PTY read EIO (child exited)")
                        asyncio.ensure_future(_finish())
                    # EAGAIN (11) just means no more data right now, stay registered
                else:
                    logger.warning("PTY read error: %s", e)
                    asyncio.ensure_future(_finish())

        try:
            loop.add_reader(fd, _on_readable)
            # Keep the task alive until runtime stops
            while self._alive:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
        finally:
            if self._master_fd is not None:
                try:
                    loop.remove_reader(self._master_fd)
                except Exception:
                    pass
