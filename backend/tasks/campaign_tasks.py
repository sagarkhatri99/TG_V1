import asyncio
import logging
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, UserIsBotError, UserBlockedError

from celery_app import celery_app
from database import SessionLocal
from models import Campaign, CampaignUserInteraction, CampaignLog, CampaignMessageTracking, TelegramAccount
from core.session_manager import session_manager
from core.account_protection import rate_limiter

logger = logging.getLogger(__name__)

# --- Campaign Task Logic ---

@celery_app.task(bind=True, max_retries=1)
def start_campaign_task(self, campaign_id: int):
    """
    Initializes and manages the campaign execution flow.
    It doesn't send messages directly but schedules individual message tasks
    to be robust and scalable.
    """
    db: Session = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign or campaign.status != "running":
            logger.info(f"Campaign {campaign_id} not running or not found. Stopping.")
            return

        # 1. Fetch pending targets
        # We prioritize targets that are 'pending'
        pending_interactions = db.query(CampaignUserInteraction).filter(
            CampaignUserInteraction.campaign_id == campaign_id,
            CampaignUserInteraction.status == "pending"
        ).limit(50).all() # Process in batches

        if not pending_interactions:
            logger.info(f"Campaign {campaign_id}: No pending interactions found.")
            # If no pending, maybe check if we are done?
            # For now, we assume if 0 pending, we wait or stop.
            # In a real engine, we'd check if we need to scrape more or if all are 'completed'
            return

        # 2. Schedule message tasks
        # We schedule them with delays to spread load
        current_delay = 0
        account_id = campaign.telegram_account_id

        for interaction in pending_interactions:
            # Check account health/limits before scheduling
            # (Double check in the task itself, but good to check here too)

            # Calculate dynamic delay
            base_delay = random.randint(campaign.min_delay, campaign.max_delay)
            current_delay += base_delay

            # Schedule the send task
            # We use 'campaign_high' queue for priority
            eta = datetime.utcnow() + timedelta(seconds=current_delay)

            send_message_task.apply_async(
                args=[campaign.id, interaction.id],
                eta=eta,
                queue='campaign_high'
            )

            # Mark interaction as 'scheduled' (or 'queued') so we don't pick it up again immediately
            interaction.status = "queued"
            db.commit()

        logger.info(f"Campaign {campaign_id}: Scheduled {len(pending_interactions)} messages.")

        # 3. Re-queue this manager task to run again after the batch is processed
        # This creates a loop that processes the campaign in chunks
        # We estimate time: current_delay + buffer
        next_run_delay = current_delay + 30
        start_campaign_task.apply_async(
            args=[campaign_id],
            countdown=next_run_delay,
            queue='campaign_medium'
        )

    except Exception as e:
        logger.error(f"Error in start_campaign_task {campaign_id}: {e}", exc_info=True)
        # Log error to campaign
        if campaign:
             _log_campaign_event(db, campaign_id, None, "error", f"Manager task failed: {str(e)}")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def send_message_task(self, campaign_id: int, interaction_id: int):
    """
    Sends a single message to a target.
    Handles auth, rate limiting, and errors.
    """
    db: Session = SessionLocal()
    account_id = None
    client = None

    try:
        # Load Data
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        interaction = db.query(CampaignUserInteraction).filter(CampaignUserInteraction.id == interaction_id).first()

        if not campaign or not interaction:
            logger.error("Campaign or Interaction not found.")
            return

        if campaign.status != "running":
            logger.info(f"Campaign {campaign_id} paused/stopped. Skipping message to {interaction.target_user_id}")
            # Revert status to pending so it can be picked up later
            interaction.status = "pending"
            db.commit()
            return

        account_id = campaign.telegram_account_id
        account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()

        # Protection Checks
        is_safe, reason = rate_limiter.check_rate_limits(account_id)
        if not is_safe:
            logger.warning(f"Rate limit hit for account {account_id}: {reason}. Re-queuing.")
            # Re-queue with backoff
            raise self.retry(countdown=300) # Retry in 5 mins

        # Get Client
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            client = loop.run_until_complete(session_manager.get_client(account))
        except Exception as auth_err:
            logger.error(f"Auth failed for account {account_id}: {auth_err}")
            interaction.status = "failed"
            _log_campaign_event(db, campaign_id, interaction_id, "error", "Auth failed")
            db.commit()
            return

        # Determine Message Content
        # Simple logic: Get template for Phase A (default)
        # In a real app, logic would pick based on interaction.current_phase
        templates = campaign.message_templates # List of dicts or strings?
        # Assuming list of strings or dicts from schema. Let's assume list of objects for now based on FE
        # Fallback to simple text if structure varies
        message_text = "Hello!"
        if isinstance(templates, list) and len(templates) > 0:
             # Just grab first one for Phase A
             # TODO: Enhance template selection logic
             tpl = templates[0]
             if isinstance(tpl, dict):
                 message_text = tpl.get("content", "Hello!")
             else:
                 message_text = str(tpl)

        # Send Message
        async def _send():
            async with client:
                target = interaction.target_username or int(interaction.target_user_id) if interaction.target_user_id.isdigit() else interaction.target_user_id
                await client.send_message(target, message_text)

        try:
            loop.run_until_complete(_send())

            # Success
            interaction.status = "sent"
            interaction.last_interaction_at = datetime.utcnow()
            campaign.sent_count += 1

            # Track message
            tracking = CampaignMessageTracking(
                campaign_user_interaction_id=interaction.id,
                message_number=1, # Phase A
                idempotency_key=f"{campaign_id}_{interaction_id}_{datetime.utcnow().timestamp()}",
                status="sent"
            )
            db.add(tracking)

            _log_campaign_event(db, campaign_id, interaction_id, "sent", "Message sent successfully")

            # Update Rate Limiter
            rate_limiter.update_account_stats(account_id, messages_sent=1)

        except FloodWaitError as e:
            logger.warning(f"FloodWait {e.seconds}s for account {account_id}")
            rate_limiter.handle_flood_incident(account_id, e.seconds, campaign_id)
            raise self.retry(countdown=e.seconds + 10)

        except (UserPrivacyRestrictedError, UserBlockedError, UserIsBotError) as e:
            logger.info(f"Delivery failed to {interaction.target_user_id}: {type(e).__name__}")
            interaction.status = "failed"
            campaign.failed_count += 1
            _log_campaign_event(db, campaign_id, interaction_id, "failed", str(e))

        except Exception as e:
            logger.error(f"Unexpected send error: {e}")
            interaction.status = "failed"
            campaign.failed_count += 1
            _log_campaign_event(db, campaign_id, interaction_id, "failed", f"Unexpected: {str(e)}")

        db.commit()

    except Exception as e:
        logger.error(f"Task error: {e}", exc_info=True)
        # Only retry on system errors, not logic errors
        # self.retry(...)
    finally:
        db.close()
        # Clean up loop if created
        # In Celery prefork, loop handling is tricky. session_manager.get_client handles basic caching.


@celery_app.task(bind=True)
def start_reply_listener(self):
    """
    Periodic task to check for new replies on active campaign accounts.
    """
    db: Session = SessionLocal()
    # Logic to iterate over active campaign accounts and check for new messages
    # This is a placeholder for the listener logic.
    # In a real implementation, this would either:
    # 1. Start a long-running process (not ideal for Celery task)
    # 2. Or, more commonly with Telethon, we fetch history since last check.

    # Simplified 'Fetch Updates' approach
    try:
        active_campaigns = db.query(Campaign).filter(Campaign.status == "running").all()
        account_ids = set(c.telegram_account_id for c in active_campaigns)

        for acc_id in account_ids:
            # Dispatch a sub-task to check specific account to avoid blocking this main loop
            check_account_replies.delay(acc_id)

    finally:
        db.close()

@celery_app.task
def check_account_replies(account_id: int):
    """
    Checks a specific account for new incoming messages that match campaign targets.
    """
    # Implementation of reply checking (fetching history)
    # ...
    pass


def _log_campaign_event(db: Session, campaign_id: int, interaction_id: int, action: str, details: str):
    try:
        log = CampaignLog(
            campaign_id=campaign_id,
            campaign_user_interaction_id=interaction_id,
            action=action,
            details={"message": details},
            created_at=datetime.utcnow()
        )
        db.add(log)
        # Commit handled by caller usually, but safe to add here
    except Exception as e:
        logger.error(f"Failed to log event: {e}")
