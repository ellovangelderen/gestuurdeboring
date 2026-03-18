"""Database aanmaken — run eenmalig vóór seed.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base, engine  # noqa: E402

# Importeer alle modellen zodat SQLAlchemy de tabellen kent
import app.core.models  # noqa: F401
import app.project.models  # noqa: F401
import app.order.models  # noqa: F401
import app.rules.models  # noqa: F401


def main():
    Base.metadata.create_all(bind=engine)
    print("Database aangemaakt.")


if __name__ == "__main__":
    main()
