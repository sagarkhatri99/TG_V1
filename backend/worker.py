import asyncio
import logging
from sqlalchemy.orm import Session
from database import get_db
from models import Job
from group_monitor.service import execute_group_monitor_job
from auto_promo.service import execute_auto_promo_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JOB_DISPATCHER = {
    'group_monitor': execute_group_monitor_job,
    'auto_promo': execute_auto_promo_job,
}

async def main():
    logger.info("Starting worker...")
    while True:
        db: Session = next(get_db())
        try:
            pending_jobs = db.query(Job).filter(Job.status == 'pending').all()
            if pending_jobs:
                logger.info(f"Found {len(pending_jobs)} pending jobs.")
                for job in pending_jobs:
                    if job.job_type in JOB_DISPATCHER:
                        logger.info(f"Starting job {job.id} of type {job.job_type}")
                        # Mark job as running to prevent re-pickup
                        job.status = 'processing' # A temporary status
                        db.commit()
                        # Pass a new db session to the job
                        job_db_session = next(get_db())
                        asyncio.create_task(JOB_DISPATCHER[job.job_type](job, job_db_session))
                    else:
                        logger.error(f"Unknown job type: {job.job_type} for job {job.id}")
                        job.status = 'failed'
                        job.error_message = f"Unknown job type: {job.job_type}"
                        db.commit()
            else:
                # This log can be noisy, so we can reduce its frequency or level
                # logger.info("No pending jobs found. Waiting...")
                pass
        except Exception as e:
            logger.error(f"An error occurred in the worker loop: {e}")
        finally:
            db.close()

        await asyncio.sleep(10) # Poll every 10 seconds

if __name__ == "__main__":
    asyncio.run(main())
