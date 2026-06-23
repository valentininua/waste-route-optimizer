from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.services.route_processor import optimize_job

logger = logging.getLogger(__name__)


async def run_optimization_task(route_job_id: int, run_id: int) -> None:
    """Run long route processing in FastAPI/Starlette background task.

    The function is async on purpose: Starlette can await async background
    callables directly, so we do not need asyncio.run(). This avoids nested
    event-loop failures under ASGI workers.
    """
    db = SessionLocal()
    try:
        await optimize_job(db, route_job_id, run_id=run_id)
    except Exception:
        logger.exception("Optimization background task failed", extra={"route_job_id": route_job_id, "run_id": run_id})
    finally:
        db.close()
