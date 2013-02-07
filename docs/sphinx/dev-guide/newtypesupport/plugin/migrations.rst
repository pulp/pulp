==========
Migrations
==========

From time to time, you might wish to adjust the schema of your database objects. The Pulp platform provides
a migration system to assist you with this process. In this section of the guide, we will discuss how to
configure your project's migrations.

Registration
============

Whether or not you plan to write any migrations, it is very important that you configure your project so that
Pulp's migration system is aware of it. This is important because Pulp only tracks schema versions on projects
that it knows about, and Pulp will always automatically migrate users to the latest available version the
first time it becomes aware of any particular project on a user's system. This is done so that new users of
a project don't need to run historical migrations on their new, empty database. By registering your project
with Pulp before you have any migrations, you can ensure that anyone who installs your project will be marked
as being at schema version 0 for your project.

To illustrate why this is important, suppose that you did not register with Pulp's migration system, and
suppose that some users have installed your package. Now suppose that you do want to make a schema change, so
you write a migration at version 1. Now when you configure your project to register with Pulp, those users
will automatically be marked as being at version 1, *without* running the migration for version 1.

How to Register
---------------

There are a few steps you will need to perform in order to configure your project to advertise itself to
Pulp's migration system. First of all, you will need to create a migrations Python package in your project's
plugin space. For example, the Pulp RPM project has its migrations at ``pulp_rpm.migrations``. You don't have
to call it "migrations", but that's a reasonable choice of name.

Secondly, you will need to use the
`Python entry points system <http://packages.python.org/distribute/pkg_resources.html#entry-points>`_ to
advertise your migration package to Pulp. To do that, add an entry_points argument to in your `setup()`
function in your setup.py file, like this::

	setup(<other_arguments>, entry_points = {
    	<other_entry_points>,
        'pulp.server.db.migrations': [
            '<your_project_name> = <path.to.migrations.package>'
        ]
    })

It's important that the entry point name "pulp.server.db.migrations" be used here. To clarify this with an
example, the Pulp RPM project's setup.py has this as it's entry_points setup argument::

	entry_points = {
        'pulp.distributors': [
            'distributor = pulp_rpm.plugins.distributors.iso_distributor.distributor:entry_point',
        ],
        'pulp.importers': [
            'importer = pulp_rpm.plugins.importers.iso_importer.importer:entry_point',
        ],
        'pulp.server.db.migrations': [
            'pulp_rpm = pulp_rpm.migrations'
        ]
    }

Once you have that in your `setup()` function, you will need to install your package using your setup.py
file. This will advertise your package's migrations to Pulp, and you will be registered with Pulp's migration
system. Once you have installed your package, you should run ``pulp-manage-db``, and you should see some
output that mentions your migration package::

	# pulp-manage-db  
	Beginning database migrations.
	Migration package pulp.server.db.migrations is up to date at version 2
	Migration package pulp_rpm.migrations is up to date at version 4
	Migration package <path.to.migrations.package> is up to date at version 0
	Database migrations complete.
	Loading content types.
	Content types loaded.

It should say that your package is at version 0, because you haven't written any migrations yet. We'll talk
about that next.

Creating Migrations
===================

In the event that you need to make an adjustment to your data in Pulp, you should write a migration script.
There are a few rules to follow for migration scripts and if you follow them carefully, nobody gets hurt.
Here are the rules:

#. Migration scripts should be modules in your migrations package.
#. Each migration module should be named starting with a version number.
#. Your migration version numbers are significant. Pulp tracks which version each install has been migrated
   to. It requires your migration versions to start with 1, and to be sequential with no gaps in version
   numbers. For example, 0001_my_first_migration.py, 0002_my_second_migration.py,
   0003_add_email_addresses_to_users.py, etc.
#. Each migration module should have a function called migrate with this signature:
   def migrate(\*args, \*\*kwargs).
#. Inside your ``migrate()`` function, you can perform the necessary work to change the data in the Pulp
   install.

For example, your migrations package might look like this::

	migrations
	|
	|-- 0001_rename_user_to_username.py
	|-- 0002_remove_spaces_from_username.py
	|-- 0003_recalculate_unit_hashes.py

Here's what the first migration, 0001_rename_user_to_username.py, might look like::

	# Getting the db handle is left as an exercise for the reader
	from somewhere import initialize_db
	
	def migrate(*args, **kwargs):
		"""
		We want to rename the 'user' attribute in our users collection to 'username' for clarity.
		"""
		db = initialize_db()
		db.users.update({}, {'$rename': {'user': 'username'}})