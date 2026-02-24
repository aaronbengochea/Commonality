from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # TODO: Implement message handling in Phase 3
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        pass
