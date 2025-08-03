import os
import hashlib
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import shutil
import logging
import time

# Configure logging
logger = logging.getLogger(__name__)

class PrivacyManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def mask_student_id(self, student_id):
        salt = os.getenv('FERPA_SALT', 'default_salt')
        masked = hashlib.blake2b(
            f"{student_id}{salt}".encode(),
            digest_size=4
        ).hexdigest()
        return f"S{masked.upper()}"
    
    def schedule_deletion(self, delete_time):
        self.scheduler.add_job(
            self._cleanup_data,
            'date',
            run_date=delete_time
        )
        logger.info(f"Scheduled data deletion at {delete_time}")
    
    def _cleanup_data(self):
        logger.info("Initiating data cleanup...")
        # Delete input data
        folders_to_clean = ['temp/', 'teacher_audio/', 'reports/']
        for folder in folders_to_clean:
            try:
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                    os.makedirs(folder, exist_ok=True)
                    logger.info(f"Cleaned {folder}")
            except Exception as e:
                logger.error(f"Error cleaning {folder}: {str(e)}")
        
        # Log deletion
        with open('deletion.log', 'a') as log:
            log.write(f"Data cleaned at {datetime.datetime.now()}\n")
        
        logger.info("Data cleanup completed")