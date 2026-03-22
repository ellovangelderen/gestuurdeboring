"""Ops endpoint — systeem status voor agents en admin dashboard.

Beveiligd met OPS_KEY environment variabele.
Gebruik: GET /api/ops/status?key=<OPS_KEY>

Geeft volledige systeeminfo als JSON:
- Database: pad, grootte, tabel counts, recente wijzigingen
- Volume: /data/ status, vrije ruimte
- App: versie, ENV, uptime, Python versie
- Deployment: git commit, branch
- Errors: recente auth failures, laatste exceptions
"""
import os
import platform
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_db, engine

router = APIRouter(prefix="/api/ops")

OPS_KEY = os.getenv("OPS_KEY", "")
_start_time = time.time()


def _require_ops_key(key: str = Query("")) -> str:
    """Valideer OPS_KEY."""
    if not OPS_KEY:
        raise HTTPException(503, "OPS_KEY niet geconfigureerd")
    if key != OPS_KEY:
        raise HTTPException(401, "Ongeldige OPS_KEY")
    return key


@router.get("/status")
def ops_status(
    key: str = Depends(_require_ops_key),
    db: Session = Depends(get_db),
):
    """Volledige systeem status — voor builder/release agents."""
    from app.order.models import Order, Boring, TracePunt, KLICUpload
    from app.admin.models import Klant

    # ── Database ──
    db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite:", "")
    db_file = Path(db_path)
    db_exists = db_file.exists()
    db_size_mb = round(db_file.stat().st_size / 1024 / 1024, 2) if db_exists else 0

    # Tabel counts
    counts = {
        "orders": db.query(Order).count(),
        "boringen": db.query(Boring).count(),
        "tracepunten": db.query(TracePunt).count(),
        "klic_uploads": db.query(KLICUpload).count(),
        "klanten": db.query(Klant).count(),
    }

    # Recente orders (laatste 7 dagen)
    nu = datetime.now(timezone.utc).replace(tzinfo=None)
    week = nu - timedelta(days=7)
    recente = db.query(Order).filter(Order.ontvangen_op >= week).count()

    # Order status verdeling
    status_counts = {}
    for row in db.execute(text("SELECT status, COUNT(*) FROM orders GROUP BY status")).fetchall():
        status_counts[row[0]] = row[1]

    # ── Volume ──
    data_dir = Path("/data")
    volume_info = {
        "mount_path": "/data",
        "exists": data_dir.exists(),
        "db_on_volume": db_path.startswith("/data"),
    }
    if data_dir.exists():
        try:
            stat = os.statvfs("/data")
            volume_info["total_mb"] = round(stat.f_frsize * stat.f_blocks / 1024 / 1024)
            volume_info["free_mb"] = round(stat.f_frsize * stat.f_bavail / 1024 / 1024)
            volume_info["used_pct"] = round((1 - stat.f_bavail / stat.f_blocks) * 100, 1)
        except Exception:
            pass

        # Logo's op volume
        logos_dir = data_dir / "logos"
        volume_info["logos"] = sorted(f.name for f in logos_dir.iterdir()) if logos_dir.exists() else []

    # ── App ──
    uptime_sec = round(time.time() - _start_time)
    uptime_str = f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s"

    # Git info (als .git of GIT_COMMIT beschikbaar)
    git_commit = os.getenv("RAILWAY_GIT_COMMIT_SHA", "")
    git_branch = os.getenv("RAILWAY_GIT_BRANCH", "")
    git_message = os.getenv("RAILWAY_GIT_COMMIT_MESSAGE", "")

    # ── Auth failures ──
    from app.core.auth import _auth_failures
    auth_info = {u: len(f) for u, f in _auth_failures.items() if f}

    # ── Audit log (laatste 20) ──
    audit = []
    try:
        from app.core.audit import AuditLog
        for entry in db.query(AuditLog).order_by(AuditLog.tijdstip.desc()).limit(20).all():
            audit.append({
                "tijdstip": str(entry.tijdstip),
                "gebruiker": entry.gebruiker,
                "actie": entry.actie,
                "entiteit": entry.entiteit,
                "detail": entry.detail,
            })
    except Exception:
        pass

    # ── Alles samenstellen ──
    return JSONResponse({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": {
            "env": settings.ENV,
            "python": platform.python_version(),
            "uptime": uptime_str,
            "uptime_sec": uptime_sec,
        },
        "deployment": {
            "git_commit": git_commit[:8] if git_commit else "",
            "git_branch": git_branch,
            "git_message": git_message[:100] if git_message else "",
            "railway_service": os.getenv("RAILWAY_SERVICE_NAME", ""),
        },
        "database": {
            "path": db_path,
            "exists": db_exists,
            "size_mb": db_size_mb,
            "counts": counts,
            "recente_orders_7d": recente,
            "status_verdeling": status_counts,
        },
        "volume": volume_info,
        "auth": {
            "failures": auth_info,
            "users_configured": len([k for k in ["USER_MARTIEN_PASSWORD", "USER_SOPA_PASSWORD", "USER_LUCAS_PASSWORD", "USER_TEST_PASSWORD"] if getattr(settings, k, "")]),
        },
        "audit_log": audit,
    })


@router.get("/health")
def ops_health(key: str = Depends(_require_ops_key)):
    """Snelle health check met meer detail dan /health."""
    db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite:", "")
    db_file = Path(db_path)
    volume_ok = Path("/data").exists()
    db_ok = db_file.exists() and db_file.stat().st_size > 0

    healthy = db_ok and volume_ok
    return JSONResponse(
        {"healthy": healthy, "db": db_ok, "volume": volume_ok, "env": settings.ENV},
        status_code=200 if healthy else 503,
    )
