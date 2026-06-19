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

from app.local_users import LocalUser
from app.terminal.runtime import Runtime

logger = logging.getLogger(__name__)


class HostRuntime(Runtime):
    def __init__(self) -> None:
        self._master_fd: int | None = None
        self._pid: int | None = None
        self._username: str | None = None
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
        local_user: LocalUser | None = None,
    ) -> None:
        if self._alive:
            raise RuntimeError("Runtime is already running")

        if local_user is None:
            try:
                username = getpass.getuser()
            except Exception:
                username = os.environ.get("USER", "user")
            uid = os.getuid()
            gid = os.getgid()
            home = os.environ.get("HOME", pwd.getpwuid(uid).pw_dir)
        else:
            username = local_user.username
            uid = local_user.uid
            gid = local_user.gid
            home = local_user.home

        current_uid = os.getuid()
        needs_user_switch = uid != current_uid
        if needs_user_switch and current_uid != 0:
            current_username = pwd.getpwuid(current_uid).pw_name
            raise PermissionError(
                "Cannot start terminal as local user "
                f"'{username}' from current process user '{current_username}'. "
                "Run MebTTY as root to create terminals for local users."
            )

        self._username = username

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
            if needs_user_switch:
                os.initgroups(username, gid)
                os.setgid(gid)
                os.setuid(uid)
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

    def current_username(self) -> str | None:
        foreground_pgid = self._foreground_pgid()
        if foreground_pgid is not None:
            foreground_pid = self._pid_for_group(foreground_pgid)
            if foreground_pid is not None:
                username = self._username_for_pid(foreground_pid)
                if username:
                    return username
        return self._username

    def current_process_name(self) -> str | None:
        if self._pid is None:
            return None

        foreground_pgid = self._foreground_pgid()
        if foreground_pgid is not None:
            foreground_pid = self._pid_for_group(foreground_pgid)
            if foreground_pid is not None:
                process_name = self._process_name(foreground_pid)
                if process_name:
                    return process_name

        return self._process_name(self._pid)

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

    def _foreground_pgid(self) -> int | None:
        if self._master_fd is None:
            return None
        try:
            pgid = os.tcgetpgrp(self._master_fd)
            return pgid if pgid > 0 else None
        except OSError:
            return None

    def _pid_for_group(self, pgid: int) -> int | None:
        candidates: list[tuple[bool, int, int]] = []
        try:
            proc_entries = os.listdir("/proc")
        except OSError:
            return None

        for entry in proc_entries:
            if not entry.isdigit():
                continue
            pid = int(entry)
            stat = self._process_stat(pid)
            if stat is None or stat["pgrp"] != pgid:
                continue
            candidates.append((pid == self._pid, stat["start_time"], pid))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], -item[1]))
        return candidates[0][2]

    def _process_stat(self, pid: int) -> dict[str, int] | None:
        try:
            with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as stat_file:
                text = stat_file.read()
            fields = text.rsplit(")", 1)[1].strip().split()
            return {
                "pgrp": int(fields[2]),
                "start_time": int(fields[19]),
            }
        except (OSError, IndexError, ValueError):
            return None

    def _process_name(self, pid: int) -> str | None:
        command_line = self._process_command_line(pid)
        if command_line:
            detected_agent = self._detect_agent_process(command_line)
            if detected_agent:
                return detected_agent

            command = os.path.basename(command_line[0])
            if command:
                return command

        try:
            with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as comm_file:
                return comm_file.read().strip()
        except OSError:
            return None

    def _process_command_line(self, pid: int) -> list[str]:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as cmdline_file:
                raw = cmdline_file.read()
        except OSError:
            return []

        return [
            part.decode("utf-8", errors="ignore")
            for part in raw.split(b"\0")
            if part
        ]

    def _detect_agent_process(self, command_line: list[str]) -> str | None:
        normalized = " ".join(command_line).lower()
        agent_markers = [
            ("codex-linux-sandbox", "codex"),
            ("codex", "codex"),
            ("claude-code", "claude-code"),
            ("claudecode", "claude-code"),
            ("claude", "claude-code"),
            ("anthropic", "claude-code"),
            ("openai", "codex"),
            ("chatgpt", "codex"),
        ]
        for marker, process_name in agent_markers:
            if marker in normalized:
                return process_name
        return None

    def _username_for_pid(self, pid: int) -> str | None:
        try:
            uid = os.stat(f"/proc/{pid}").st_uid
            return pwd.getpwuid(uid).pw_name
        except (OSError, KeyError):
            return None

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
