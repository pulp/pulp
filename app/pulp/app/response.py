from rest_framework.response import Response


class OperationPostponedResponse(Response):
    """
    An HTTP response class for returning 202 and a list of spawned tasks.

    This reponse object should be used by views that dispatch asynchronous tasks. The most common
    use case is for sync and publish operations. When JSON is requested, the response will look
    like the following:

        [
            {
                "_href": "/this/needs/to/be/updated/adlfk-bala-23k5l7-lslser",
                "task_id": "adlfk-bala-23k5l7-lslser"
            },
            {
                "_href": "/this/needs/to/be/updated/fr63x-dlsd-4566g-dv64m",
                "task_id": "fr63x-dlsd-4566g-dv64m"
            }
        ]
    """

    def __init__(self, task_results):
        """
        :param task_results: List of AsyncResult objects that are used to generate the response.
        :type task_group_id: List of AsyncResult
        """
        raise NotImplementedError
        tasks = []
        for result in task_results:
            task = {"_href": result.task_id, "task_id": result.task_id}
            tasks.append(task)
        super(OperationPostponedResponse, self).__init__(data=tasks, status=202)
