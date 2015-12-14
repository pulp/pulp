from pulp.server.db.migrate.models import MigrationRemovedError


def migrate(*args, **kwargs):
    raise MigrationRemovedError('0006', '2.8.0', '2.4.0')
