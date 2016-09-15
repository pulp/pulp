from django import apps


class PulpAppConfig(apps.AppConfig):
    # The app's importable name
    name = 'pulp.app'
    # The app label to be used when creating tables, registering models,
    # referencing this app with manage.py, etc. This cannot contain a dot,
    # so for brevity's sake it's just "pulp", rather than e.g. "pulp_app".
    label = 'pulp'
