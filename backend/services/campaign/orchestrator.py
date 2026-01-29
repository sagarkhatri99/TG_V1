import logging
from sqlalchemy.orm import Session
from models import Job, Campaign
from celery.result import AsyncResult
from celery.exceptions import CeleryError

logger = logging.getLogger(__name__)

def create_parent_job(campaign: Campaign, user_id: int, db: Session) -> Job:
    """
    Create parent job for campaign and flush to DB (not committed).
    Returns Job object with ID assigned.
    """
    try:
        job = Job(
            user_id=user_id,
            telegram_account_id=campaign.telegram_account_id,
            job_type='campaign',
            status='in_progress',
            user_description=f"Campaign: {campaign.name}",
            config=str({
                'campaign_id': campaign.id,
                'min_delay': campaign.min_delay,
                'max_delay': campaign.max_delay
            })
        )
        db.add(job)
        db.flush()  # Get ID without committing
        return job
    except Exception as e:
        logger.error(f"Failed to create parent job for campaign {campaign.id}: {e}")
        raise

def start_campaign_orchestration(job_id: int, campaign_config: dict, queue: str = 'campaign_high') -> AsyncResult:
    """
    Dispatch campaign initialization to Celery.
    Returns AsyncResult or raises CeleryError.
    """
    from tasks.campaign_tasks import initialize_campaign

    logger.info(f"Dispatching campaign {campaign_config['campaign_id']} to queue {queue}")

    try:
        # We set retry=False here because if dispatch fails, we want to know immediately to rollback DB
        result = initialize_campaign.apply_async(
            kwargs={'job_id': job_id, 'campaign_id': campaign_config['campaign_id']},
            queue=queue,
            retry=False
        )

        if not result:
            raise CeleryError("apply_async returned None")

        logger.info(f"Task dispatched: {result.id}")
        return result

    except Exception as e:
        logger.error(f"Dispatch failed: {e}")
        raise CeleryError(f"Failed to dispatch: {str(e)}")
