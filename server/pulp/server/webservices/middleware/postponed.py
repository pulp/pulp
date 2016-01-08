import logging

from celery.result import AsyncResult
from django.http import HttpResponse

from pulp.server.async.tasks import TaskResult
from pulp.server.compat import json, json_util
from pulp.server.exceptions import OperationPostponed
from pulp.server.webservices.views.serializers import dispatch


_LOG = logging.getLogger(__name__)


class PostponedOperationMiddleware(object):
    """
    Catch OperationPostponed exceptions and return an HTTP Accepted response
    along with the proper serialization of the asynchronous call information.
    """

    @staticmethod
    def _get_operation_postponed_body(exception):
        report = exception.call_report
        if isinstance(exception.call_report, AsyncResult):
            report = TaskResult.from_async_result(exception.call_report)
        serialized_call_report = report.serialize()
        if 'spawned_tasks' in serialized_call_report:
            for task in serialized_call_report['spawned_tasks']:
                href_obj = dispatch.task_result_href(task)
                task.update(href_obj)

        # Use the object's serializer if it is a Mongoengine Document.
        result = serialized_call_report.get('result')
        if hasattr(result, 'SERIALIZER'):
            serialized_call_report['result'] = result.SERIALIZER(result).data

        return json.dumps(serialized_call_report, default=json_util.default)

    def process_exception(self, request, exception):
        """
        Process the catched exception.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param exception: OperationPostponed
        :type exception: Exception

        :return: Response containing processed exception
        :rtype: django.http.HttpResponse
        """

        if isinstance(exception, OperationPostponed):
            body = self._get_operation_postponed_body(exception)
            status = exception.http_status_code
            response_obj = HttpResponse(body, status=status,
                                        content_type="application/json; charset=utf-8")
            return response_obj
