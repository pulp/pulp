"""
This is where we connect our plugin to Pulp. Having `PulpPluginAppConfig` as a parent class
identifies this app as a Pulp plugin. We specify the location our app so it may be
installed.
"""
from pulp.app.apps import PulpPluginAppConfig


class TestAppConfig(PulpPluginAppConfig):
    name = 'pulp.app.tests.testapp'
    label = 'testapp'
