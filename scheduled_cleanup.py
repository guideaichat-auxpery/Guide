#!/usr/bin/env python3
"""
Scheduled Data Retention Cleanup Script
Run this script periodically (e.g., weekly via cron) to enforce data retention policies.

Australian Privacy Act 1988 APP 11 compliance:
- 7-year retention for general student records and conversations
- 25-year retention for child safety records
- Permanent retention for audit logs

Usage:
    python scheduled_cleanup.py [--dry-run]
    
Options:
    --dry-run   Show what would be deleted without actually deleting
"""

import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_cleanup(dry_run=False):
    """Execute data retention cleanup."""
    from database import (
        get_db, 
        cleanup_old_conversations, 
        cleanup_old_student_activities,
        cleanup_old_planning_notes,
        RETENTION_YEARS_DEFAULT
    )
    
    logger.info("=" * 60)
    logger.info("Starting scheduled data retention cleanup")
    logger.info(f"Retention period: {RETENTION_YEARS_DEFAULT} years")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 60)
    
    db = get_db()
    if not db:
        logger.error("Failed to connect to database")
        return False
    
    try:
        total_deleted = 0
        
        if dry_run:
            logger.info("[DRY RUN] Would cleanup old conversations")
            logger.info("[DRY RUN] Would cleanup old activities")
            logger.info("[DRY RUN] Would cleanup old planning notes")
        else:
            conversations_deleted = cleanup_old_conversations(db)
            logger.info(f"Deleted {conversations_deleted} old conversation records")
            total_deleted += conversations_deleted
            
            activities_deleted = cleanup_old_student_activities(db)
            logger.info(f"Deleted {activities_deleted} old activity records")
            total_deleted += activities_deleted
            
            notes_deleted = cleanup_old_planning_notes(db)
            logger.info(f"Deleted {notes_deleted} old planning notes")
            total_deleted += notes_deleted
        
        logger.info("=" * 60)
        logger.info(f"Cleanup completed. Total records deleted: {total_deleted}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    success = run_cleanup(dry_run=dry_run)
    sys.exit(0 if success else 1)
