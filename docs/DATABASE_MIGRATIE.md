# Database Migratiestrategie

## Huidige aanpak: startup migraties in lifespan()

SQLite + `create_all()` bij startup maakt nieuwe tabellen maar geen nieuwe kolommen in bestaande tabellen. Daarom:

1. **Nieuwe tabel** → automatisch via `Base.metadata.create_all()`
2. **Nieuwe kolom** → handmatig toevoegen aan `migrations` lijst in `app/main.py` lifespan()
3. **Referentiedata** → auto-seeden in lifespan() met `if count() == 0`

### Checklist bij model-wijziging

- [ ] Kolom toegevoegd aan SQLAlchemy model
- [ ] `ALTER TABLE` statement toegevoegd aan lifespan() migrations lijst
- [ ] Referentiedata seed toegevoegd als het een nieuwe tabel met defaults is
- [ ] Getest op verse database (verwijder hdd.db en herstart)
- [ ] Getest op bestaande database (herstart zonder hdd.db te verwijderen)

### Migratie-lijst (app/main.py)
```python
migrations = [
    "ALTER TABLE orders ADD COLUMN vergunning_checklist TEXT",
    "ALTER TABLE boringen ADD COLUMN revisie INTEGER DEFAULT 0",
    "ALTER TABLE trace_punten ADD COLUMN variant INTEGER DEFAULT 0",
]
```

## Toekomstig: Alembic

Bij grotere schema-wijzigingen (kolom hernoemen, type wijzigen, data migreren) overstappen op Alembic:

```bash
alembic revision --autogenerate -m "beschrijving"
alembic upgrade head
```

Alembic configuratie is aanwezig maar migraties zijn niet up-to-date.
