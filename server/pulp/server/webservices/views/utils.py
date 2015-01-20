import json


def generate_django_response(response, content=None, default=None, content_type='application/json'):
    """
    Serialize an object and return a djagno response

    :param response    : Django response ojbect
    :type  response    : HttpResponse or subclass
    :param content     : content to be serialized
    :type  content     : anything that is serializable by json.dumps
    :param default     : function used by json_dumps to serialize content
    :type  default     : function or None
    :param content_type: type of returned content
    :type  content_type: str

    :raises            : TypeError if response is not a valid Django response object
    :return            : response containing the serialized content
    :rype              : HttpResponse
    """
    json_obj = json.dumps(content, default=default)
    return response(json_obj, content_type=content_type)

