"""Order router — aggregeert alle sub-routers.

Alle URLs blijven identiek: /orders/...
De sub-routers staan in app/order/routers/.
"""
from fastapi import APIRouter

from app.order.routers import (
    cockpit,
    order_crud,
    boring_crud,
    trace,
    brondata,
    asbuilt,
    vergunning,
    varianten,
    analyse,
    exports,
    werkplan,
)

router = APIRouter(prefix="/orders")

# Volgorde is belangrijk: statische paden (/nieuw, /import, /export/csv, /statusmail)
# moeten VOOR /{order_id} staan, anders worden ze als order_id geïnterpreteerd.
router.include_router(cockpit.router)
router.include_router(order_crud.router)
router.include_router(boring_crud.router)
router.include_router(trace.router)
router.include_router(brondata.router)
router.include_router(asbuilt.router)
router.include_router(vergunning.router)
router.include_router(varianten.router)
router.include_router(analyse.router)
router.include_router(exports.router)
router.include_router(werkplan.router)

# Backward-compatible imports voor tests en andere modules
from app.order.routers.cockpit import _genereer_statusmail_concepten  # noqa: F401, E402
from app.order.routers.varianten import varianten_pagina  # noqa: F401, E402
from app.order.helpers import templates, _f, _i, _STATUS_MAP, _ACTIEVE_STATUSSEN  # noqa: F401, E402
from app.order.helpers import UPLOAD_DIR, MAX_KLIC_SIZE, MAX_IMAGE_SIZE, MAX_EXCEL_SIZE  # noqa: F401, E402
