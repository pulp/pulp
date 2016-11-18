from celery import task

from pulp.app.models import Publisher
from pulp.tasking import UserFacingTask

@task(base=UserFacingTask)
def delete_publisher(repo_name, publisher_name):
     Publisher.objects.filter(name=publisher_name, repository__name=repo_name).delete()
