import logging

from fastapi import APIRouter, WebSocket

from app.terminal.ws_handler import websocket_endpoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminal")


@router.websocket("/ws/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    await websocket_endpoint(websocket, session_id)
