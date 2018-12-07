from rest_framework.views import APIView

from pulpcore.app.response import OperationPostponedResponse
from pulpcore.app.tasks import orphan_cleanup
from pulpcore.tasking.tasks import enqueue_with_reservation


class OrphansView(APIView):

    def delete(self, request, format=None):
        """
        Cleans up all the Content and Artifact orphans in the system
        """
        async_result = enqueue_with_reservation(orphan_cleanup, [])

        return OperationPostponedResponse(async_result, request)
