import os

from celery import Celery
from celery.schedules import crontab
from decouple import config
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", config("DJANGO_SETTINGS_MODULE"))

app = Celery("koda")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# # Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# app.autodiscover_tasks()
app.conf.beat_schedule = {
    "notify-free-tier-users-every-day": {
        "task": "user_engagement.tasks.notify_users_nearing_free_limit",
        "schedule": crontab(hour=0, minute=0),  # Every midnight
    },
    "notify-inactive-paid-users-weekly": {
        "task": "user_engagement.tasks.notify_inactive_paid_users",
        "schedule": crontab(day_of_week=1, hour=0, minute=0),  # Every Monday
    },
    "request-feedback-from-active-users-weekly": {
        "task": "user_engagement.tasks.send_satisfaction_survey",
        "schedule": crontab(day_of_week=3, hour=0, minute=0),  # Every Wednesday
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
