import asyncio
import json
import logging
import struct

from fastapi import WebSocket, WebSocketDisconnect

from app.terminal.manager import RuntimeManager

logger = logging.getLogger(__name__)

# Opcodes
OPCODE_INPUT = 0x01
OPCODE_OUTPUT = 0x02
OPCODE_RESIZE = 0x03
OPCODE_HEARTBEAT = 0x04
OPCODE_CLOSE = 0x05
OPCODE_ERROR = 0x06
OPCODE_CWD = 0x07
OPCODE_STATUS = 0x08


def encode_packet(opcode: int, payload: bytes) -> bytes:
    """Encode a packet: [opcode(1 byte)][length(4 bytes big-endian)][payload]."""
    header = struct.pack("!BI", opcode, len(payload))
    return header + payload


def decode_packet(data: bytes) -> tuple[int, bytes]:
    """Decode a packet, returning (opcode, payload)."""
    if len(data) < 5:
        raise ValueError("Packet too short: need at least 5 bytes")
    opcode, length = struct.unpack("!BI", data[:5])
    payload = data[5 : 5 + length]
    if len(payload) != length:
        raise ValueError(
            f"Packet payload mismatch: expected {length} bytes, got {len(payload)}"
        )
    return opcode, payload


async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    manager = RuntimeManager()
    runtime = await manager.get_runtime(session_id)

    if runtime is None or not runtime.is_alive:
        error_msg = f"No active runtime found for session '{session_id}'"
        error_packet = encode_packet(OPCODE_ERROR, error_msg.encode("utf-8"))
        await websocket.send_bytes(error_packet)
        await websocket.close(code=4001, reason=error_msg)
        logger.warning("WebSocket rejected: %s", error_msg)
        return

    logger.info("WebSocket connected for session '%s'", session_id)

    reader_task = asyncio.create_task(
        _runtime_reader(websocket, runtime, session_id)
    )
    writer_task = asyncio.create_task(
        _websocket_reader(websocket, runtime, session_id)
    )
    status_task = asyncio.create_task(
        _status_watcher(websocket, runtime, session_id)
    )

    try:
        done, pending = await asyncio.wait(
            [reader_task, writer_task, status_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # Cancel the other task
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        # Re-raise exceptions from completed tasks
        for task in done:
            if task.exception() and not isinstance(
                task.exception(), (WebSocketDisconnect, asyncio.CancelledError)
            ):
                raise task.exception()
    except Exception:
        logger.exception("Error in WebSocket handler for session '%s'", session_id)
    finally:
        # Cancel remaining tasks just in case
        for task in [reader_task, writer_task, status_task]:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Mark session as detached — do NOT destroy runtime (for session recovery)
        logger.info(
            "WebSocket disconnected for session '%s', runtime preserved for recovery",
            session_id,
        )

        # Update session status to DETACHED
        try:
            from app.database import async_session_factory
            from app.session.service import SessionService

            async with async_session_factory() as db:
                await SessionService.update_session_status(db, session_id, "detached")
                await db.commit()
                logger.info("Session '%s' marked as DETACHED", session_id)
        except Exception:
            logger.warning("Failed to update session '%s' status to DETACHED", session_id, exc_info=True)


async def _runtime_reader(websocket: WebSocket, runtime, session_id: str) -> None:
    """Read from runtime and send OUTPUT packets to websocket."""
    try:
        async for data in runtime.read():
            packet = encode_packet(OPCODE_OUTPUT, data)
            await websocket.send_bytes(packet)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected while sending for session '%s'", session_id)
    except Exception:
        logger.exception(
            "Error reading from runtime for session '%s'", session_id
        )


async def _status_watcher(websocket: WebSocket, runtime, session_id: str) -> None:
    last_cwd: str | None = None
    last_status: dict[str, str] | None = None
    try:
        while runtime.is_alive:
            cwd = runtime.current_cwd()
            if cwd and cwd != last_cwd:
                last_cwd = cwd
                packet = encode_packet(OPCODE_CWD, cwd.encode("utf-8"))
                await websocket.send_bytes(packet)
                await _persist_session_cwd(session_id, cwd)

            status = {
                "cwd": cwd or "",
                "username": runtime.current_username() or "",
            }
            if status != last_status:
                last_status = status
                packet = encode_packet(
                    OPCODE_STATUS,
                    json.dumps(status, separators=(",", ":")).encode("utf-8"),
                )
                await websocket.send_bytes(packet)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected while watching status for session '%s'", session_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Error watching status for session '%s'", session_id)


async def _persist_session_cwd(session_id: str, cwd: str) -> None:
    try:
        from app.database import async_session_factory
        from app.models import Session
        from sqlalchemy import select

        async with async_session_factory() as db:
            result = await db.execute(select(Session).where(Session.id == session_id))
            session = result.scalar_one_or_none()
            if session is not None and session.cwd != cwd:
                session.cwd = cwd
                await db.commit()
    except Exception:
        logger.debug("Failed to persist cwd for session '%s'", session_id, exc_info=True)


async def _websocket_reader(websocket: WebSocket, runtime, session_id: str) -> None:
    """Read from websocket and forward to runtime."""
    try:
        while True:
            data = await websocket.receive_bytes()
            opcode, payload = decode_packet(data)

            if opcode == OPCODE_INPUT:
                await runtime.write(payload)
            elif opcode == OPCODE_RESIZE:
                if len(payload) >= 4:
                    cols, rows = struct.unpack("!HH", payload[:4])
                    await runtime.resize(cols, rows)
                    logger.debug(
                        "Resized session '%s' to %dx%d", session_id, cols, rows
                    )
                else:
                    logger.warning("Invalid RESIZE payload for session '%s'", session_id)
            elif opcode == OPCODE_HEARTBEAT:
                heartbeat_response = encode_packet(OPCODE_HEARTBEAT, payload)
                await websocket.send_bytes(heartbeat_response)
            elif opcode == OPCODE_CLOSE:
                logger.info("Received CLOSE for session '%s'", session_id)
                break
            else:
                logger.warning(
                    "Unknown opcode 0x%02x from session '%s'", opcode, session_id
                )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected while reading for session '%s'", session_id)
