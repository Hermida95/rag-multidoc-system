import asyncio
import uuid

from app.container import build_process_document_use_case
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.infrastructure.db.session import AsyncSessionFactory

logger = get_logger(__name__)


@celery_app.task(
    name="app.infrastructure.celery.tasks.process_document_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def process_document_task(document_id: str) -> None:
    """Celery entrypoint: runs the async ingestion pipeline to completion
    inside a dedicated event loop, since Celery workers are synchronous.
    """
    asyncio.run(_run(document_id))


async def _run(document_id: str) -> None:
    async with AsyncSessionFactory() as session:
        try:
            use_case = build_process_document_use_case(session)
            await use_case.execute(uuid.UUID(document_id))
            await session.commit()
        except Exception:
            await session.rollback()
            logger.error("process_document_task_failed", document_id=document_id)
            raise
