"""Gedeelde helpers, constanten en templates voor order routers."""
from pathlib import Path
from typing import Optional

from fastapi.templating import Jinja2Templates

from app.order.klantcodes import ORDER_STATUSES

templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_KLIC_SIZE = 50 * 1024 * 1024      # 50 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024      # 10 MB
MAX_EXCEL_SIZE = 20 * 1024 * 1024      # 20 MB

_STATUS_MAP = {s["value"]: s["label"] for s in ORDER_STATUSES}

# Statussen die als "actief" gelden (niet geleverd/afgerond/geannuleerd)
_ACTIEVE_STATUSSEN = {"order_received", "in_progress", "waiting_for_approval"}


def _f(v: str) -> Optional[float]:
    """Converteer leeg Form string-veld naar None (optionele float)."""
    return float(v) if v and v.strip() else None


def _i(v: str) -> Optional[int]:
    """Converteer leeg Form string-veld naar None (optionele int)."""
    return int(v) if v and v.strip() else None


def _parse_checklist(json_str) -> dict:
    if not json_str:
        return {}
    try:
        import json
        return json.loads(json_str)
    except Exception:
        return {}
