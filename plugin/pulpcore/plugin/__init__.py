# plugins declare that they are a pulp plugin by subclassing PulpPluginAppConfig
from pulpcore.app.apps import PulpPluginAppConfig

# Allow plugin writers to subclass PulpException
from pulpcore.exceptions import PulpException  # NOQA
