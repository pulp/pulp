from rest_framework.views import APIView

from pulpcore.app.response import OperationPostponedResponse
from pulpcore.app.tasks import orphan_cleanup


class OrphansView(APIView):

    def delete(self, request, format=None):
        """
        Cleans up all the Content and Artifact orphans in the system
        """
        async_result = orphan_cleanup.apply_async_with_reservation([])

        return OperationPostponedResponse(async_result, request)
