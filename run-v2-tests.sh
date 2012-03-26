# Runs unit tests and generates a coverage report for all v2 related code

# Please keep the following in alphabetical order so it's easier to determine
# if something is in the list

PACKAGES="pulp.gc_client.framework.loader,pulp.gc_client.framework.core,pulp.gc_client.framework.exceptions,pulp.server.managers,pulp.server.content,pulp.server.db.model.gc_repository,pulp.server.db.model.gc_content,pulp.server.webservices.controllers.gc_contents,pulp.server.webservices.controllers.gc_plugins,pulp.server.webservices.controllers.gc_repositories,pulp.server.dispatch.call,pulp.server.dispatch.coordinator,pulp.server.dispatch.factory,pulp.server.dispatch.history,pulp.server.dispatch.scheduler,pulp.server.dispatch.task,pulp.server.dispatch.taskqueue,pulp.server.managers.user"
TESTS="test/unit/test_base_distributor_conduit.py \
       test/unit/test_base_importer_conduit.py \
       test/unit/test_client_framework_core.py \
       test/unit/test_content_managers.py \
       test/unit/test_content_plugin_loader.py \
       test/unit/test_dispatch_call.py \
       test/unit/test_dispatch_coordinator.py \
       test/unit/test_dispatch_scheduler.py \
       test/unit/test_dispatch_task.py \
       test/unit/test_dispatch_taskqueue.py \
       test/unit/test_gc_client_exception_handler.py \
       test/unit/test_extensions_loader.py \
       test/unit/test_repo_controller.py \
       test/unit/test_repo_importer_manager.py \
       test/unit/test_repo_manager.py \
       test/unit/test_repo_publish_conduit.py \
       test/unit/test_repo_publish_manager.py \
       test/unit/test_repo_query_manager.py \
       test/unit/test_repo_sync_conduit.py \
       test/unit/test_repo_sync_manager.py \
       test/unit/test_repo_unit_association_manager.py \
       test/unit/test_repo_unit_association_query_manager.py \
       test/unit/test_types_database.py \
       test/unit/test_types_parser.py \
       test/unit/test_unit_import_conduit.py \
       test/unit/test_user_manager.py \
       test/plugins/yum_importer/test_rpms.py \
       test/plugins/yum_importer/test_errata.py 
       "

nosetests --with-coverage --cover-html  --cover-erase --cover-package $PACKAGES $TESTS
