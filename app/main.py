from __future__ import annotations

import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, baselines, health, sensors, sessions
from app.config import get_settings
from app.websocket.manager import manager


logging.basicConfig(level=logging.INFO)

settings = get_settings()
app = FastAPI(
    title="PC3 Vision Gateway",
    description="Vision and sensor gateway for smart mirror AIoT coaching.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(baselines.router)
app.include_router(sensors.router)
app.include_router(analyze.router)


@app.websocket("/ws/sessions/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str) -> None:
    await manager.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
