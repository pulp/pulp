import json


class ParseBodyMiddleware(object):

    def process_request(self, request):
        """
        Parse body as json, and save the json as body_as_json attribute on request object.

        :param request: A django WSGI request object from the Django middleware
        :type request: django.core.handlers.wsgi.WSGIRequest
        """
        try:
            request.body_as_json = json.loads(request.body)
        except ValueError:
            request.body_as_json = {}
