class DelegateDecorator:
    """
    Delegation decorator.
    Any decorated method may be implemented by the download delegate.

    Attributes:
        decorated: The decorated method (function).
        enabled (bool): Dispatch to the delegate is enabled.
            Used to prevent recursion when delegate calls back into the download.
        download (pulpcore.download.Download): A download object.

    Examples:
        >>>
        >>> class ErrorHandler:
        >>>     def on_error(self, download, error):
        >>>         ...
        >>>         repaired = True # Fixed the problem so retry.
        >>>         return repaired
        >>>
        >>> download = ... # <Download>
        >>> download.delegate = ErrorHandler()
        >>>

    See Also:
        [1] https://en.wikipedia.org/wiki/Delegation_(object-oriented_programming)
    """

    def __init__(self, decorated):
        """
        Args:
            decorated: The decorated method function.
        """
        self.__doc__ = decorated.__doc__
        self.__repr__ = decorated.__repr__
        self.decorated = decorated
        self.enabled = True
        self.download = None

    @property
    def name(self):
        """
        The name of the decorated method.

        Returns:
            (str): The method name.
        """
        return self.decorated.__name__

    def select_method(self):
        """
        Select the actual method to be invoked.

        Returns:
            The identically named method on the delegate when defined.
            Else, the decorated method's function.
        """
        method = self.decorated
        try:
            if self.enabled:
                method = getattr(self.download.delegate, self.name.lstrip('_'))
        except AttributeError:
            pass
        return method

    def __call__(self, *args, **kwargs):
        """
        Delegate the method call.
          - find the appropriate method.
          - disable self to prevent recursion.
          - invoke the method.
          - enable self
        """
        method = self.select_method()
        try:
            self.enabled = False
            return method(self.download, *args, **kwargs)
        finally:
            self.enabled = True

    def __get__(self, instance, owner):
        """
        Using python descriptors to assign the download attribute when the
        decorated method is referenced.

        Args:
            instance (pulpcore.download.Download): The decorated instance.
            owner (class): The decorated class.

        Returns:
            Delegate: self
        """
        self.download = instance
        return self


# Alias lowercase.
delegate = DelegateDecorator
