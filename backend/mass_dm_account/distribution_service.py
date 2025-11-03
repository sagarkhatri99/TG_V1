"""Service for distributing Mass DM jobs across multiple accounts."""
import json
import logging
from typing import List, Tuple
from models import Job, TelegramAccount, User
from database import SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


def distribute_users_across_accounts(
    user_ids: List[str],
    account_ids: List[int],
    current_user: User,
    db: Session,
) -> Tuple[List[int], int, int]:
    """
    Distribute a list of user IDs evenly across multiple accounts.
    
    Args:
        user_ids: List of user IDs/usernames to distribute
        account_ids: List of account IDs to distribute across
        current_user: The current user object
        db: Database session
    
    Returns:
        Tuple of (created_job_ids, total_users, users_per_account)
    
    Raises:
        ValueError: If accounts are invalid or don't belong to user
        Exception: If account validation fails
    """
    
    # Validate all accounts exist and belong to the user
    accounts = db.query(TelegramAccount).filter(
        TelegramAccount.id.in_(account_ids),
        TelegramAccount.user_id == current_user.id
    ).all()
    
    if len(accounts) != len(account_ids):
        raise ValueError("One or more accounts not found or don't belong to user")
    
    # Verify all accounts are active
    inactive_accounts = [a for a in accounts if a.status != 'active']
    if inactive_accounts:
        inactive_ids = [a.id for a in inactive_accounts]
        raise ValueError(f"The following accounts are not active: {inactive_ids}")
    
    if not user_ids:
        raise ValueError("No user IDs provided")
    
    if not account_ids:
        raise ValueError("No accounts selected")
    
    # Calculate batch size
    total_users = len(user_ids)
    num_accounts = len(account_ids)
    batch_size = total_users // num_accounts
    remainder = total_users % num_accounts
    
    logger.info(
        f"Distributing {total_users} users across {num_accounts} accounts. "
        f"Batch size: {batch_size}, Remainder: {remainder}"
    )
    
    # Create a parent job to track the distribution
    parent_job = Job(
        user_id=current_user.id,
        telegram_account_id=None,
        job_type='mass_dm_account_distributed',
        config=json.dumps({
            "total_users": total_users,
            "num_accounts": num_accounts,
            "account_ids": account_ids,
        }),
        status='pending',
        user_description=f"Distribution master job for {total_users} users across {num_accounts} accounts",
        messages_planned=total_users,
    )
    db.add(parent_job)
    db.commit()
    db.refresh(parent_job)
    
    created_job_ids = []
    
    # Create batch jobs for each account
    for i, account_id in enumerate(account_ids):
        # Calculate this batch's user IDs
        start_idx = i * batch_size
        if i == num_accounts - 1:
            # Last account gets the remainder
            end_idx = total_users
        else:
            end_idx = start_idx + batch_size
        
        batch_users = user_ids[start_idx:end_idx]
        batch_number = i + 1
        
        logger.info(
            f"Creating batch job {batch_number}/{num_accounts} for account {account_id}. "
            f"Users: {len(batch_users)} (indices {start_idx}-{end_idx})"
        )
        
        # Create the batch job
        batch_job = Job(
            user_id=current_user.id,
            telegram_account_id=account_id,
            job_type='mass_dm_account',
            config=json.dumps({}),
            status='pending',
            user_description=f"Batch {batch_number}/{num_accounts} - {len(batch_users)} users",
            messages_planned=len(batch_users),
            parent_job_id=parent_job.id,
            batch_number=batch_number,
            total_batches=num_accounts,
            batch_user_ids=json.dumps(batch_users),
        )
        db.add(batch_job)
        db.commit()
        db.refresh(batch_job)
        
        created_job_ids.append(batch_job.id)
    
    logger.info(
        f"Successfully created {len(created_job_ids)} batch jobs. "
        f"Parent job ID: {parent_job.id}"
    )
    
    return created_job_ids, total_users, batch_size
