# backend/app/routers/kite.py
from fastapi import APIRouter
import os
from pathlib import Path
from dotenv import load_dotenv
import requests
from datetime import datetime
from app.services import kite_ws_manager as manager

router = APIRouter(prefix="/kite", tags=["kite"])

# ===== Setup .env loader =====
BASE_DIR = Path(__file__).resolve().parents[2]   # backend/
DOTENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=DOTENV_PATH, override=True)


# ===== Helper: Download instruments file =====
def download_instruments():
    """
    Downloads the latest Zerodha instruments file and always overwrites
    backend/instruments.csv (no backup).
    """
    try:
        instruments_url = "https://api.kite.trade/instruments"
        resp = requests.get(instruments_url, timeout=30)
        if resp.status_code == 200:
            backend_dir = Path(__file__).resolve().parents[2]   # backend/
            latest_path = backend_dir / "instruments.csv"

            with open(latest_path, "wb") as f:
                f.write(resp.content)

            return {
                "status": "ok",
                "message": "Instrument list updated",
                "latest_file": str(latest_path)
            }
        else:
            return {"status": "error", "message": f"Failed {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===== Routes =====
@router.get("/status")
def kite_status():
    """
    Show whether API key and access token are loaded from .env.
    """
    api_key = os.getenv("KITE_API_KEY", "").strip().strip('"')
    access_token = os.getenv("KITE_ACCESS_TOKEN", "").strip().strip('"')
    return {
        "api_key": api_key,
        "access_token_loaded": bool(access_token),
        "access_token_preview": access_token[:6] + "..." if access_token else None,
    }


@router.post("/reload-access-token")
def reload_access_token():
    """
    Force backend to reload KITE_ACCESS_TOKEN from .env
    Restart WebSocket connection.
    Also download the latest instruments file.
    """
    access_token = os.getenv("KITE_ACCESS_TOKEN", "").strip().strip('"')
    if not access_token:
        return {"status": "error", "message": "KITE_ACCESS_TOKEN missing in .env"}

    # Update runtime
    os.environ["KITE_ACCESS_TOKEN"] = access_token
    manager.ACCESS_TOKEN = access_token

    # Restart WebSocket with fresh token
    manager._start_ws()

    # Download latest instruments file on reload
    instruments_result = download_instruments()

    return {
        "status": "ok",
        "message": "Access token reloaded from .env & WebSocket restarted",
        "access_token_preview": access_token[:6] + "..." if access_token else None,
        "instruments": instruments_result,
    }


@router.api_route("/refresh-instruments", methods=["GET", "POST"])
def refresh_instruments():
    """
    Manually download latest instruments file from Zerodha.
    Supports both GET (browser) and POST (API clients).
    """
    result = download_instruments()
    return {
        "status": result.get("status"),
        "message": result.get("message", ""),
        "latest_file": result.get("latest_file"),
        "backup_file": result.get("backup_file")
    }
