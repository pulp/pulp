from .... import base
from pulp.server.db.migrate.models import MigrationModule
from pulp.server.db.model.consumer import Bind


class BindAdditionMigrationTests(base.PulpServerTests):

    def clean(self):
        super(BindAdditionMigrationTests, self).clean()

        Bind.get_collection().remove()

    def test_upgrade(self):
        # Setup
        coll = Bind.get_collection()

        for counter in range(0, 3):
            bind_dict = {
                'consumer_id': 'consumer_%s' % counter,
                'repo_id': 'repo_%s' % counter,
                'distributor_id': 'distributor_%s' % counter,
            }

            coll.insert(bind_dict)

        # Test
        module = MigrationModule('pulp.server.db.migrations.0003_bind_additions')._module
        module.migrate()

        # Verify
        bindings = coll.find()
        for b in bindings:
            self.assertTrue('notify_agent' in b)
            self.assertEqual(b['notify_agent'], True)
            self.assertTrue('binding_config' in b)
            self.assertEqual(b['binding_config'], None)

    def test_upgrade_idempotency(self):
        """
        Simplest way to check the migration can run twice is simply to run it twice. The
        primary goal is to make sure an exception isn't raised.
        """

        # Setup
        coll = Bind.get_collection()

        for counter in range(0, 3):
            bind_dict = {
                'consumer_id': 'consumer_%s' % counter,
                'repo_id': 'repo_%s' % counter,
                'distributor_id': 'distributor_%s' % counter,
            }

            coll.insert(bind_dict)

        # Test
        module = MigrationModule('pulp.server.db.migrations.0003_bind_additions')._module
        module.migrate()
        module.migrate()

        # Verify
        bindings = coll.find()
        for b in bindings:
            self.assertTrue('notify_agent' in b)
            self.assertEqual(b['notify_agent'], True)
            self.assertTrue('binding_config' in b)
            self.assertEqual(b['binding_config'], None)
