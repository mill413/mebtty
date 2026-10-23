import asyncio
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.terminal.host_runtime import HostRuntime


class TerminalLocaleTest(unittest.IsolatedAsyncioTestCase):
    async def _shell_locale(self, inherited, startup=""):
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"LANG", "LANGUAGE"} and not key.startswith("LC_")
        }
        environment.update(inherited)

        with tempfile.TemporaryDirectory() as directory:
            shell = Path(directory) / "locale-shell"
            shell.write_text(
                "#!/bin/sh\n"
                f"{startup}\n"
                "printf '%s\\n' \"${LANG-unset}\" \"${LC_ALL-unset}\" "
                "\"${LC_MESSAGES-unset}\"\n"
            )
            shell.chmod(0o700)
            runtime = HostRuntime()
            with patch.dict(os.environ, environment, clear=True):
                await runtime.start(str(shell), cwd=directory)
            try:
                async def collect():
                    return b"".join([chunk async for chunk in runtime.read()])

                output = await asyncio.wait_for(collect(), timeout=5)
                return output.decode().splitlines()
            finally:
                await runtime.stop()

    async def test_inherits_language_without_forcing_lc_all(self):
        output = await self._shell_locale({"LANG": "zh_CN.UTF-8"})

        self.assertEqual(output, ["zh_CN.UTF-8", "unset", "unset"])

    async def test_shell_startup_can_choose_language(self):
        output = await self._shell_locale(
            {"LANG": "en_US.UTF-8"}, startup="export LANG=zh_CN.UTF-8"
        )

        self.assertEqual(output, ["zh_CN.UTF-8", "unset", "unset"])

    async def test_preserves_explicit_locale_overrides(self):
        output = await self._shell_locale({
            "LANG": "zh_CN.UTF-8",
            "LC_ALL": "C.UTF-8",
            "LC_MESSAGES": "en_US.UTF-8",
        })

        self.assertEqual(output, ["zh_CN.UTF-8", "C.UTF-8", "en_US.UTF-8"])


if __name__ == "__main__":
    unittest.main()
