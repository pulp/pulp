# Runs unit tests and generates a coverage report for all v2 related code

# Please keep the following in alphabetical order so it's easier to determine
# if something is in the list

PACKAGES="pulp.gc_client.framework.core"
PACKAGES="$PACKAGES,pulp.gc_client.agent.lib"
PACKAGES="$PACKAGES,pulp.gc_client.framework.exceptions"
PACKAGES="$PACKAGES,pulp.gc_client.framework.loader"
PACKAGES="$PACKAGES,pulp.server.content"
PACKAGES="$PACKAGES,pulp.server.db.model.gc_content"
PACKAGES="$PACKAGES,pulp.server.db.model.gc_repository"
PACKAGES="$PACKAGES,pulp.server.dispatch.call"
PACKAGES="$PACKAGES,pulp.server.dispatch.coordinator"
PACKAGES="$PACKAGES,pulp.server.dispatch.factory"
PACKAGES="$PACKAGES,pulp.server.dispatch.history"
PACKAGES="$PACKAGES,pulp.server.dispatch.scheduler"
PACKAGES="$PACKAGES,pulp.server.dispatch.task"
PACKAGES="$PACKAGES,pulp.server.dispatch.taskqueue"
PACKAGES="$PACKAGES,pulp.server.gc_agent"
PACKAGES="$PACKAGES,pulp.server.managers"
PACKAGES="$PACKAGES,pulp.server.webservices.controllers.gc_consumers"
PACKAGES="$PACKAGES,pulp.server.webservices.controllers.gc_contents"
PACKAGES="$PACKAGES,pulp.server.webservices.controllers.gc_plugins"
PACKAGES="$PACKAGES,pulp.server.webservices.controllers.gc_repositories"
PACKAGES="$PACKAGES,pulp.server.webservices.controllers.gc_root_actions"
PACKAGES="$PACKAGES,pulp_tasks"
PACKAGES="$PACKAGES,rpm_sync"
PACKAGES="$PACKAGES,rpm_units_copy"

TESTS="test/unit/test_agent.py \
       test/unit/test_base_distributor_conduit.py \
       test/unit/test_base_importer_conduit.py \
       test/unit/test_client_framework_core.py \
       test/unit/test_consumer_controller.py \
       test/unit/test_consumer_manager.py \
       test/unit/test_content_managers.py \
       test/unit/test_content_plugin_loader.py \
       test/unit/test_content_orphan_manager.py \
       test/unit/test_content_upload_manager.py \
       test/unit/test_contents_controller.py \
       test/unit/test_dispatch_call.py \
       test/unit/test_dispatch_coordinator.py \
       test/unit/test_dispatch_scheduler.py \
       test/unit/test_dispatch_task.py \
       test/unit/test_dispatch_taskqueue.py \
       test/unit/test_gc_client_exception_handler.py \
       test/unit/test_extensions_loader.py \
       test/unit/test_handler_container.py \
       test/unit/test_manager_factory.py \
       test/unit/test_plugin_manager.py \
       test/unit/test_plugin_controller.py \
       test/unit/test_pulp_tasks_extension.py \
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
       test/unit/test_rpm_units_copy_extension.py \
       test/unit/test_root_actions_controller.py \
       test/unit/test_schedule_cud_manager.py \
       test/unit/test_schedule_commands.py \
       test/unit/test_types_database.py \
       test/unit/test_types_parser.py \
       test/unit/test_unit_import_conduit.py \
       test/unit/test_user_manager.py \
       test/plugins/yum_importer/test_drpms.py \
       test/plugins/yum_importer/test_repo_scratchpad.py \
       test/plugins/yum_importer/test_rpms.py \
       test/plugins/yum_importer/test_errata.py
       "

nosetests --with-coverage --cover-html  --cover-erase --cover-package $PACKAGES $TESTS
