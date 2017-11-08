from rest_framework.response import Response
from rest_framework.reverse import reverse


class OperationPostponedResponse(Response):
    """
    An HTTP response class for returning 202 and a list of spawned tasks.

    This response object should be used by views that dispatch asynchronous tasks. The most common
    use case is for sync and publish operations. When JSON is requested, the response will look
    like the following::

        [
            {
                "_href": "https://example.com/api/v3/tasks/adlfk-bala-23k5l7-lslser",
                "task_id": "adlfk-bala-23k5l7-lslser"
            },
            {
                "_href": "https://example.com/api/v3/tasks/fr63x-dlsd-4566g-dv64m",
                "task_id": "fr63x-dlsd-4566g-dv64m"
            }
        ]
    """

    def __init__(self, task_results, request):
        """
        Args:
            task_results (list): List of :class:`celery.result.AsyncResult` objects used to
                                 generate the response.
            request (rest_framework.request.Request): Request used to generate the _href urls
        """
        tasks = []
        for result in task_results:
            task = {"_href": reverse('tasks-detail', args=[result.task_id], request=request),
                    "task_id": result.task_id}
            tasks.append(task)
        super(OperationPostponedResponse, self).__init__(data=tasks, status=202)
