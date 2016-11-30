
class Request:
    """
    An ABSTRACT download request.

    Attributes:
        url (str): A file download URL.
        destination (str): An absolute path to where the downloaded file is stored.
        validators (list): A list of registered validators.
        error_handler (ErrorHandler): An optional error handler.
        attachment : Arbitrary object attached to the request.
        scratchpad (dict): A shared scratchpad for things like sessions and tokens.

    Notes:
        The validators are applied in order.

    """

    def __init__(self, url, destination):
        """
        Args:
            url (str): A file download URL.
            destination (str): An absolute path to where the downloaded file is stored.

        """
        self.url = url
        self.destination = destination
        self.validators = []
        self.error_handler = ErrorHandler()
        self.attachment = None
        self.scratchpad = {}

    def __call__(self):
        """
        Execute the request.

        Notes:
            Must be implemented by subclass.
        """
        raise NotImplementedError()

    def succeeded(self):
        """
        Get whether the request has succeeded.

        Returns:
            bool: True if succeeded.

        """
        return not self.failed()

    def failed(self):
        """
        Get whether the request has failed.

        Returns:
            bool: True if failed.

        Notes:
            Must be implemented by subclass.

        """
        raise NotImplementedError()

    def on_succeeded(self, result):
        """
        Handle a successful download result.
        Performs validation.

        Args:
            result: The protocol specific result.

        """
        for validator in self.validators:
            validator(self)

    def on_failed(self, result):
        """
        Handle a failed download result.
        Delegated to the ErrorHandler.

        Args:
            result: The protocol specific result.

        """
        self.error_handler(self, result)


class ErrorHandler:
    """
    Handler error conditions.
    """

    def __call__(self, request):
        """
        The specified request has an error condition.
        This handler is given opportunity remedy the condition and retry the request.

        Args:
            request (Request): A request with an error condition.

        Examples:

            As overridden by subclass:

            >>>
            >>> class RetryHandler(ErrorHandler):
            >>>
            >>>     def __init__(self, retries=1):
            >>>         self.retries = retries
            >>>
            >>>     def __call__(self, request):
            >>>         if self.retries < 1:
            >>>             # Done
            >>>             return
            >>>         token = ...
            >>>         request.headers['token'] = token
            >>>         self.retries -= 1
            >>>         request()

        """
        pass
