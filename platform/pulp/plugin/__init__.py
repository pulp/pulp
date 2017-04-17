# plugins declare that they are a pulp plugin by subclassing PulpPluginAppConfig
from pulp.app.apps import PulpPluginAppConfig

# Allow plugin writers to subclass PulpException
from pulp.exceptions import PulpException  # NOQA
