class Delegate:
    """
    Delegation decorator.

    Attributes:
        decorated: The decorated method function.
        enabled (bool): Dispatch to the delegate is enabled.
            Used to prevent recursion when delegate calls back into the download.
        download (Download): A download object.
    """

    def __init__(self, decorated):
        """
        Args:
            decorated: The decorated method function.
        """
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

    def method(self):
        """
        The method to be invoked.

        Returns:
            The identically named method on the delegate when defined.
            Else, the decorated method's function.
        """
        method = self.decorated
        try:
            if self.enabled:
                method = getattr(self.download.delegate, self.name)
        except AttributeError:
            pass
        return method

    def __call__(self):
        """
        Delegate the method call.
          - find the appropriate method.
          - disable self to prevent recursion.
          - invoke the method.
          - enable self
        """
        method = self.method()
        try:
            self.enabled = False
            return method(self.download)
        finally:
            self.enabled = True

    def __get__(self, instance, owner):
        self.download = instance
        return self

delegate = Delegate

