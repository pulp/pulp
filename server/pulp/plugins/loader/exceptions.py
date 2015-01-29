class PluginLoaderException(Exception):
    """
    Base plugin loader exception.
    """
    pass


class PluginLoadError(PluginLoaderException):
    """
    Raised when errors are encountered while loading plugins.
    """
    pass


class ConflictingPluginError(PluginLoaderException):
    """
    Raised when 2 or more plugins try to handle the same content, distribution,
    or profile type(s).
    """
    pass


class PluginNotFound(PluginLoaderException):
    """
    Raised when a plugin cannot be located.
    """
    pass


# derivative classes used for testing
class ConflictingPluginName(ConflictingPluginError):
    pass


class InvalidImporter(PluginLoadError):
    pass


class MalformedMetadata(PluginLoadError):
    pass


class MissingMetadata(PluginLoadError):
    pass


class MissingPluginClass(PluginLoadError):
    pass


class MissingPluginModule(PluginLoadError):
    pass


class MissingPluginPackage(PluginLoadError):
    pass


class NamespaceCollision(PluginLoadError):
    pass
