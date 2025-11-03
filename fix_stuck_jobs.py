#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')

from database import SessionLocal
from models import Job
from datetime import datetime

def fix_stuck_jobs():
    """Fix jobs that are 100% complete but still marked as running"""
    db = SessionLocal()
    try:
        # Find jobs that are 100% complete but still running
        stuck_jobs = db.query(Job).filter(
            Job.status == 'running',
            Job.completion_percentage >= 100.0
        ).all()
        
        print(f"Found {len(stuck_jobs)} stuck jobs to fix:")
        
        for job in stuck_jobs:
            print(f"  Job {job.id}: {job.completion_percentage}% complete, status: {job.status}")
            job.status = 'completed'
            if not job.completed_at:
                job.completed_at = datetime.utcnow()
            print(f"  → Fixed: Job {job.id} marked as completed")
        
        if stuck_jobs:
            db.commit()
            print(f"\n✅ Successfully fixed {len(stuck_jobs)} stuck jobs!")
        else:
            print("No stuck jobs found.")
            
    except Exception as e:
        print(f"❌ Error fixing stuck jobs: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_stuck_jobs()