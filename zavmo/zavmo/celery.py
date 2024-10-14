from __future__ import absolute_import, unicode_literals

import os
import sys
from decouple import config
from celery import Celery
from kombu import Queue, Exchange
from django.conf import settings
from celery.schedules import crontab
from dotenv import load_dotenv
load_dotenv()

import logging
from logging.handlers import RotatingFileHandler

# Extend Python path for discovering utility modules and task definitions
git_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(git_dir)

# --------------------------- Logging Configuration ---------------------------
logger = logging.getLogger('celery_tasks')
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler('celery_tasks.log', maxBytes=10 * 1024 * 1024, backupCount=1)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
# --------------------------- Redis Configuration ---------------------------

REDIS_HOST = config('REDIS_HOST', 'localhost')
REDIS_PORT = config('REDIS_PORT', 6379)
REDIS_DB  = config('REDIS_DB', 0)

CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zavmo.settings')

app = Celery('zavmo',
             broker=CELERY_BROKER_URL,
             backend=CELERY_RESULT_BACKEND,
)
app.config_from_object('django.conf:settings')


# NOTE: Will use it to schedule any periodic tasks
CELERY_BEAT_SCHEDULE = {}


# Automatically discover tasks within a given list of modules when the Celery worker starts
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.conf.update(
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='task.default',
    worker_prefetch_multiplier=4,
    task_acks_late=False,
    worker_max_memory_per_child=500000,
    worker_send_task_events=True,
    task_track_started=True,
    timezone='UTC',
    broker_heartbeat=120,
    broker_heartbeat_checkrate=2,
    broker_pool_limit=None,
    worker_max_tasks_per_child=10,
    worker_concurrency=8,
    worker_lost_wait=20,
    broker_transport_options={
        'visibility_timeout': 3600,
        'queue_order_strategy': 'priority',
        'sep': ':',
        'priority_steps': list(range(10)),
    },
    task_time_limit=60*30,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=60*60*24,
    beat_schedule=CELERY_BEAT_SCHEDULE,  # Add this line to apply the beat schedule
)

# Set up Celery worker event listener for logging
@app.task(bind=True)
def debug_task(self):
    logger.info(f'Request: {self.request!r}')

if __name__ == '__main__':
    app.start()
