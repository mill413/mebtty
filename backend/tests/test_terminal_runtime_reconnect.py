import asyncio
import unittest

from app.terminal.host_runtime import HostRuntime


class TerminalRuntimeReconnectTest(unittest.IsolatedAsyncioTestCase):
    async def _read_until(self, runtime: HostRuntime, marker: bytes) -> bytes:
        output = bytearray()
        reader = runtime.read()
        try:
            while marker not in output:
                output.extend(await asyncio.wait_for(anext(reader), timeout=2))
        finally:
            await reader.aclose()
        return bytes(output)

    async def test_output_is_buffered_without_a_websocket_reader(self):
        runtime = HostRuntime()
        await runtime.start("/bin/sh")

        try:
            await runtime.write(b"printf '__attached__\\n'\n")
            await self._read_until(runtime, b"__attached__")

            # Simulate a detached WebSocket: the PTY keeps running without a
            # consumer, and output must remain available to the next reader.
            await runtime.write(b"printf '__while_detached__\\n'\n")
            output = await self._read_until(runtime, b"__while_detached__")

            self.assertIn(b"__while_detached__", output)
            self.assertTrue(runtime.is_alive)
        finally:
            await runtime.stop()


if __name__ == "__main__":
    unittest.main()
