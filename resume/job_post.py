import time

from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task

from koda.config.logging_config import configure_logger
from resume.models import JobPost
from resume.utils.util_funcs import get_job_post_feedback, improve_doc

# Logging setup
logger = configure_logger(__name__)

SYSTEM_ROLE = "system"
USER_ROLE = "user"


# Wrap the entire asynchronous logic in a function to be called synchronously
async def optimize_job(job_post_id):
    # Use sync_to_async for database operations that are originally synchronous
    job_post_content = ""
    job_post_feedback = await get_job_post_feedback(job_post_content)

    optimized_content = await improve_doc(
        "job post", job_post_content, job_post_feedback
    )

    job_post_instance, job_post_created = await sync_to_async(
        JobPost.objects.update_or_create, thread_sensitive=True
    )(
        job_post_id=job_post_id,
        defaults={
            "original_content": job_post_content,
            "optimized_content": optimized_content,
        },
    )
    return job_post_instance.optimized_content


@shared_task
def optimize_job_post(job_post_id):
    start_time = time.time()

    # Correctly pass job_post_id to the async function
    optimized_content = async_to_sync(optimize_job)(job_post_id)
    total_time = time.time() - start_time
    logger.info(
        f"Total time taken: {total_time} seconds for job post ID {job_post_id}."
    )

    return optimized_content
