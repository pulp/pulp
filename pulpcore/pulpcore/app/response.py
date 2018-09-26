from rest_framework.response import Response
from rest_framework.reverse import reverse


class OperationPostponedResponse(Response):
    """
    An HTTP response class for returning 202 and a spawned task.

    This response object should be used by views that dispatch asynchronous tasks. The most common
    use case is for sync and publish operations. When JSON is requested, the response will look
    like the following::

        {
            "_href": "https://example.com/pulp/api/v3/tasks/adlfk-bala-23k5l7-lslser",
            "task_id": "adlfk-bala-23k5l7-lslser"
        }
    """

    def __init__(self, result, request):
        """
        Args:
            task_result (pulpcore.app.models.Task): A :class:`rq.job.Job` object used to generate
                the response.
            request (rest_framework.request.Request): Request used to generate the _href urls
        """
        task = {"task": reverse('tasks-detail', args=[result.id], request=None)}
        super().__init__(data=task, status=202)
