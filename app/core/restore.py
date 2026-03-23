"""Disaster recovery — restore database + logo's vanuit Cloudflare R2.

Gebruik:
    # CLI: restore laatste backup
    python -m app.core.restore

    # CLI: restore specifieke datum
    python -m app.core.restore --datum 2026-03-22

    # Vanuit code
    from app.core.restore import restore_from_r2
    result = restore_from_r2()
"""
import logging
import shutil
from datetime import date
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("restore")


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
    env = settings.ENV if settings.ENV in ("staging", "production") else "development"
    return f"{env}/"


def list_available_backups() -> list:
    """Lijst beschikbare backup datums in R2."""
    client = _get_r2_client()
    if not client:
        return []

    try:
        prefix = _prefix()
        response = client.list_objects_v2(Bucket=settings.R2_BUCKET, Prefix=prefix)
        datums = set()
        for obj in response.get("Contents", []):
            # key = staging/2026-03-22/hdd.db
            parts = obj["Key"].split("/")
            if len(parts) >= 2:
                datums.add(parts[1])
        return sorted(datums, reverse=True)
    except Exception as e:
        logger.error("R2 list mislukt: %s", e)
        return []


def restore_from_r2(datum: str = None) -> dict:
    """Restore database + logo's vanuit R2 backup.

    Args:
        datum: YYYY-MM-DD formaat. None = laatste beschikbare backup.

    Returns: dict met resultaten.
    """
    client = _get_r2_client()
    if not client:
        return {"ok": False, "fout": "R2 niet geconfigureerd"}

    prefix = _prefix()
    resultaat = {
        "ok": False,
        "datum": datum,
        "db_restored": False,
        "logos_restored": 0,
        "fouten": [],
    }

    # Bepaal datum
    if not datum:
        datums = list_available_backups()
        if not datums:
            resultaat["fout"] = "Geen backups gevonden in R2"
            return resultaat
        datum = datums[0]
        resultaat["datum"] = datum

    # Download DB
    db_key = f"{prefix}{datum}/hdd.db"
    db_path = Path("/data/hdd.db") if Path("/data").exists() else Path("./hdd.db")
    db_backup = db_path.with_suffix(".db.bak")

    try:
        # Maak backup van huidige DB
        if db_path.exists():
            shutil.copy2(db_path, db_backup)
            logger.info("Huidige DB gebackupt naar %s", db_backup)

        # Download van R2
        client.download_file(settings.R2_BUCKET, db_key, str(db_path))
        resultaat["db_restored"] = True
        logger.info("DB restored: %s → %s", db_key, db_path)
    except Exception as e:
        resultaat["fouten"].append(f"DB restore: {e}")
        logger.error("DB restore mislukt: %s", e)
        # Rollback
        if db_backup.exists():
            shutil.copy2(db_backup, db_path)
            logger.info("Rollback naar backup: %s", db_backup)

    # Download logo's
    logo_dir = Path("/data/logos") if Path("/data").exists() else Path("static/logos")
    logo_dir.mkdir(parents=True, exist_ok=True)

    try:
        logo_prefix = f"{prefix}{datum}/logos/"
        response = client.list_objects_v2(Bucket=settings.R2_BUCKET, Prefix=logo_prefix)
        for obj in response.get("Contents", []):
            filename = obj["Key"].split("/")[-1]
            if filename:
                dest = logo_dir / filename
                client.download_file(settings.R2_BUCKET, obj["Key"], str(dest))
                resultaat["logos_restored"] += 1
                logger.info("Logo restored: %s", filename)
    except Exception as e:
        resultaat["fouten"].append(f"Logo restore: {e}")

    resultaat["ok"] = resultaat["db_restored"] and len(resultaat["fouten"]) == 0
    return resultaat


if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Restore HDD database vanuit R2 backup")
    parser.add_argument("--datum", help="Backup datum (YYYY-MM-DD). Leeg = laatste.")
    parser.add_argument("--list", action="store_true", help="Toon beschikbare backups")
    args = parser.parse_args()

    if args.list:
        datums = list_available_backups()
        print(f"Beschikbare backups ({len(datums)}):")
        for d in datums:
            print(f"  {d}")
    else:
        print(f"Restoring {'laatste backup' if not args.datum else args.datum}...")
        result = restore_from_r2(args.datum)
        print(json.dumps(result, indent=2))
        if not result["ok"]:
            exit(1)
