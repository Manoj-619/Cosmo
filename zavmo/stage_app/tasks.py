from celery import shared_task

@shared_task
def new_celery_task():
    # task logic here
    return  