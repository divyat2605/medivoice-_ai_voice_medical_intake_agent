"""
Token server — issues short-lived LiveKit access tokens so the browser
frontend can join a call room. Run alongside the agent worker:

    python token_server.py
"""

from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from pydantic import BaseModel

load_dotenv()

LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")

app = FastAPI(title="MediVoice Token Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class TokenRequest(BaseModel):
    patient_name: str = "Patient"
    room_name: str | None = None


class TokenResponse(BaseModel):
    token: str
    url: str
    room_name: str


@app.post("/token", response_model=TokenResponse)
async def create_token(req: TokenRequest) -> TokenResponse:
    if not (LIVEKIT_API_KEY and LIVEKIT_API_SECRET and LIVEKIT_URL):
        raise HTTPException(500, "LiveKit credentials are not configured on the server.")

    room_name = req.room_name or f"intake-{uuid.uuid4().hex[:8]}"
    identity = f"{req.patient_name}-{uuid.uuid4().hex[:6]}"

    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(req.patient_name)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
        .to_jwt()
    )

    return TokenResponse(token=token, url=LIVEKIT_URL, room_name=room_name)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("TOKEN_SERVER_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
