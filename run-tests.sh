# Please keep the following in alphabetical order so it's easier to determine
# if something is in the list

# Server Code
PACKAGES="pulp"

# Builtins
PACKAGES="$PACKAGES,pulp_admin_auth"
PACKAGES="$PACKAGES,pulp_admin_consumer"
PACKAGES="$PACKAGES,pulp_consumer"
PACKAGES="$PACKAGES,pulp_repo"
PACKAGES="$PACKAGES,pulp_server_info"
PACKAGES="$PACKAGES,pulp_tasks"

# RPM Support
PACKAGES="$PACKAGES,rpm_admin_consumer"
PACKAGES="$PACKAGES,rpm_repo"
PACKAGES="$PACKAGES,rpm_sync"
PACKAGES="$PACKAGES,rpm_units_copy"
PACKAGES="$PACKAGES,rpm_units_search"
PACKAGES="$PACKAGES,rpm_upload"
PACKAGES="$PACKAGES,yum_distributor"
PACKAGES="$PACKAGES,yum_importer"

# Test Directories
TESTS="platform/test/unit builtins/test/unit rpm-support/test/unit"

nosetests --with-coverage --cover-html --cover-erase --cover-package $PACKAGES $TESTS
