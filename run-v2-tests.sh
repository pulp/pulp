# Runs unit tests and generates a coverage report for all v2 related code

# Please keep the following in alphabetical order so it's easier to determine
# if something is in the list

PACKAGES="pulp.server.managers,pulp.server.content,pulp.server.db.model.gc_repository,pulp.server.db.model.gc_content,pulp.server.webservices.controllers.gc_contents,pulp.server.webservices.controllers.gc_plugins,pulp.server.webservices.controllers.gc_repositories"
TESTS="test/unit/test_content_managers.py \
       test/unit/test_content_plugin_loader.py \
       test/unit/test_repo_controller.py \
       test/unit/test_repo_importer_manager.py \
       test/unit/test_repo_manager.py \
       test/unit/test_repo_publish_conduit.py \
       test/unit/test_repo_publish_manager.py \
       test/unit/test_repo_query_manager.py \
       test/unit/test_repo_sync_conduit.py \
       test/unit/test_repo_sync_manager.py \
       test/unit/test_repo_unit_association_manager.py \
       test/unit/test_types_database.py \
       test/unit/test_types_parser.py
       "

nosetests --with-coverage --cover-html  --cover-erase --cover-package $PACKAGES $TESTS
