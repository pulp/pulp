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

# Test Directories
TESTS="platform/test/unit builtins/test/unit "

nosetests --with-coverage --cover-html --cover-erase --cover-package $PACKAGES $TESTS
