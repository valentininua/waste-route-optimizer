from __future__ import annotations

import asyncio
import logging

from app.db.session import SessionLocal
from app.services.route_processor import optimize_job

logger = logging.getLogger(__name__)


def run_optimization_task(route_job_id: int, run_id: int) -> None:
    """
        Starts long route processing in the background.
    """
    db = SessionLocal()
    try:
        asyncio.run(optimize_job(db, route_job_id, run_id=run_id))
    except Exception:
        logger.exception("Optimization background task failed", extra={"route_job_id": route_job_id, "run_id": run_id})
    finally:
        db.close()
