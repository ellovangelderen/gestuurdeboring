web: (alembic upgrade head 2>/dev/null || echo "Migration skipped") && uvicorn app.main:app --host 0.0.0.0 --port $PORT
