"""
APScheduler setup for background jobs
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

from mcp_server.config import settings
from mcp_server.utils.logger import get_logger
from .jobs.sync_cuny_courses import sync_courses_job
from .jobs.scrape_reviews import scrape_reviews_job
from .jobs.update_professor_grades import update_grades_job


logger = get_logger(__name__)


class JobScheduler:
    """Background job scheduler"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        logger.info("Job Scheduler initialized")
    
    def setup_jobs(self):
        """Setup all scheduled jobs"""
        
        # Sync CUNY courses - Every Sunday at 2 AM
        self.scheduler.add_job(
            sync_courses_job,
            CronTrigger.from_crontab(settings.sync_schedule_cron),
            id='sync_courses',
            name='Sync CUNY Courses',
            replace_existing=True
        )
        logger.info("Added job: Sync CUNY Courses (Every Sunday 2 AM)")
        
        # Scrape professor reviews - Every Monday at 3 AM
        self.scheduler.add_job(
            scrape_reviews_job,
            CronTrigger(day_of_week='mon', hour=3, minute=0),
            id='scrape_reviews',
            name='Scrape Professor Reviews',
            replace_existing=True
        )
        logger.info("Added job: Scrape Professor Reviews (Every Monday 3 AM)")
        
        # Update professor grades - Every Monday at 5 AM
        self.scheduler.add_job(
            update_grades_job,
            CronTrigger(day_of_week='mon', hour=5, minute=0),
            id='update_grades',
            name='Update Professor Grades',
            replace_existing=True
        )
        logger.info("Added job: Update Professor Grades (Every Monday 5 AM)")
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Job Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Job Scheduler shutdown")


# Singleton instance
job_scheduler = JobScheduler()


async def main():
    """Main entry point for background jobs"""
    logger.info("Starting Background Job Scheduler")
    
    job_scheduler.setup_jobs()
    job_scheduler.start()
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        job_scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
