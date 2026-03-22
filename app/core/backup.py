"""Backup naar Cloudflare R2 — database + logo's.

Draait via:
- /admin/backup (handmatig, admin-only)
- Railway cron job (nachtelijk)

Wat het doet:
1. Kopieert hdd.db via sqlite3 .backup() API (veilig bij concurrent gebruik)
2. Upload DB + logo's naar R2 bucket met datum-prefix
3. Ruimt oude backups op (>30 dagen)
"""
import logging
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("backup")

MAX_BACKUPS = 30


def _db_path() -> Path:
    """Haal het fysieke pad van de SQLite database op."""
    path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite:", "")
    return Path(path)


def _get_r2_client():
    """Maak een boto3 S3 client voor Cloudflare R2."""
    if not settings.R2_ENDPOINT or not settings.R2_ACCESS_KEY_ID:
        return None
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def _prefix() -> str:
    """R2 key prefix op basis van environment."""
    env = settings.ENV if settings.ENV in ("staging", "production") else "development"
    return f"{env}/"


def backup_database() -> str:
    """Maak een consistente kopie van de SQLite database.

    Gebruikt sqlite3 .backup() API — veilig bij concurrent gebruik.
    Returns: pad naar lokale backup.
    """
    db_path = _db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database niet gevonden: {db_path}")

    backup_dir = Path("/data/backups") if Path("/data").exists() else Path("backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    vandaag = date.today().strftime("%Y-%m-%d")
    backup_name = f"hdd-{vandaag}.db"
    backup_path = backup_dir / backup_name

    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_path))
    src.backup(dst)
    dst.close()
    src.close()

    size_mb = round(backup_path.stat().st_size / 1024 / 1024, 2)
    logger.info("DB backup: %s (%.2f MB)", backup_path, size_mb)
    return str(backup_path)


def upload_to_r2(local_path: str, r2_key: str) -> bool:
    """Upload een bestand naar R2. Returns True als succesvol."""
    client = _get_r2_client()
    if not client:
        logger.warning("R2 niet geconfigureerd — upload overgeslagen")
        return False

    try:
        client.upload_file(local_path, settings.R2_BUCKET, r2_key)
        logger.info("R2 upload: %s → %s/%s", local_path, settings.R2_BUCKET, r2_key)
        return True
    except Exception as e:
        logger.error("R2 upload mislukt: %s", e)
        return False


def list_r2_backups() -> list:
    """Lijst alle backups in R2 bucket. Returns list van dicts."""
    client = _get_r2_client()
    if not client:
        return []

    try:
        prefix = _prefix()
        response = client.list_objects_v2(Bucket=settings.R2_BUCKET, Prefix=prefix)
        items = []
        for obj in response.get("Contents", []):
            items.append({
                "key": obj["Key"],
                "size_mb": round(obj["Size"] / 1024 / 1024, 2),
                "last_modified": obj["LastModified"].isoformat(),
            })
        return sorted(items, key=lambda x: x["key"], reverse=True)
    except Exception as e:
        logger.error("R2 list mislukt: %s", e)
        return []


def cleanup_old_backups() -> int:
    """Verwijder R2 backups ouder dan MAX_BACKUPS dagen. Returns aantal verwijderd."""
    client = _get_r2_client()
    if not client:
        return 0

    try:
        prefix = _prefix()
        response = client.list_objects_v2(Bucket=settings.R2_BUCKET, Prefix=prefix)
        objects = response.get("Contents", [])

        grens = datetime.now(objects[0]["LastModified"].tzinfo) - timedelta(days=MAX_BACKUPS) if objects else None
        verwijderd = 0

        for obj in objects:
            if grens and obj["LastModified"] < grens:
                client.delete_object(Bucket=settings.R2_BUCKET, Key=obj["Key"])
                logger.info("R2 backup verwijderd: %s", obj["Key"])
                verwijderd += 1

        # Lokale backups ook opruimen
        backup_dir = Path("/data/backups") if Path("/data").exists() else Path("backups")
        if backup_dir.exists():
            lokale_grens = datetime.now() - timedelta(days=MAX_BACKUPS)
            for f in backup_dir.glob("hdd-*.db"):
                if f.stat().st_mtime < lokale_grens.timestamp():
                    f.unlink()
                    verwijderd += 1

        return verwijderd
    except Exception as e:
        logger.error("R2 cleanup mislukt: %s", e)
        return 0


def run_backup() -> dict:
    """Voer volledige backup uit: DB + logo's → R2.

    Returns dict met resultaten.
    """
    vandaag = date.today().strftime("%Y-%m-%d")
    prefix = _prefix()
    resultaat = {
        "datum": vandaag,
        "db_backup": None,
        "db_uploaded": False,
        "logos_uploaded": 0,
        "backups_opgeruimd": 0,
        "fouten": [],
    }

    # 1. Database backup
    try:
        db_backup_path = backup_database()
        resultaat["db_backup"] = db_backup_path
        resultaat["db_uploaded"] = upload_to_r2(
            db_backup_path, f"{prefix}{vandaag}/hdd.db"
        )
    except Exception as e:
        resultaat["fouten"].append(f"DB backup: {e}")
        logger.error("DB backup mislukt: %s", e)

    # 2. Logo's uploaden
    logo_dir = Path("/data/logos") if Path("/data/logos").exists() else Path("static/logos")
    if logo_dir.exists():
        for logo_file in logo_dir.iterdir():
            if logo_file.is_file():
                try:
                    ok = upload_to_r2(
                        str(logo_file), f"{prefix}{vandaag}/logos/{logo_file.name}"
                    )
                    if ok:
                        resultaat["logos_uploaded"] += 1
                except Exception as e:
                    resultaat["fouten"].append(f"Logo {logo_file.name}: {e}")

    # 3. Oude backups opruimen
    try:
        resultaat["backups_opgeruimd"] = cleanup_old_backups()
    except Exception as e:
        resultaat["fouten"].append(f"Cleanup: {e}")

    logger.info("Backup compleet: DB=%s, logos=%d, opgeruimd=%d, fouten=%d",
                resultaat["db_uploaded"], resultaat["logos_uploaded"],
                resultaat["backups_opgeruimd"], len(resultaat["fouten"]))

    return resultaat
