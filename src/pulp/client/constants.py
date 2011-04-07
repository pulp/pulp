#
# String constants for the pulp CLI
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
#

AVAILABLE_REPOS_LIST = """
Id                 \t%-25s
Name               \t%-25s
Feed URL           \t%-25s
Feed Type          \t%-25s
Feed Certs         \t%-25s
Consumer Certs     \t%-25s
Architecture       \t%-25s
Sync Schedule      \t%-25s
Packages           \t%-25s
Files              \t%-25s
Distributions      \t%-25s
Publish            \t%-25s
Clones             \t%-25s
Groups             \t%-25s
Filters            \t%-25s
Notes              \t%-25s
"""

AVAILABLE_CONSUMER_GROUP_INFO = """
Id                 \t%-25s
Description        \t%-25s
Consumer ids       \t%-25s
Additional info    \t%-25s
"""


AVAILABLE_CONSUMER_INFO = """
Id                 \t%-25s
Description        \t%-25s
Subscribed Repos   \t%-25s
Agent:
   Responding      \t%-25s
   Last Heartbeat  \t%-25s
Additional info    \t%-25s
"""

CONSUMER_KEY_VALUE_INFO = """
\t%-15s:\t%-15s
"""


REPO_SCHEDULES_LIST = """
Label              \t%-25s
Schedule           \t%-25s
"""

PACKAGE_GROUP_INFO = """
Name                \t%-25s
Id                  \t%-25s
Mandatory packages  \t%-25s
Default packages    \t%-25s
Optional packages   \t%-25s
Conditional packages\t%-25s
"""

PACKAGE_GROUP_CATEGORY_INFO = """
Name                \t%-25s
Id                  \t%-25s
Groups              \t%-25s
"""


AVAILABLE_USERS_LIST = """
Login :               \t%-25s    
Name  :               \t%-25s
Roles :               \t%-25s
"""

AVAILABLE_FILTERS_LIST = """
Id           :               \t%-25s
Description  :               \t%-25s
Type         :               \t%-25s
Package List :               \t%-25s
"""

ERRATA_INFO = """
Id                    \t%-25s
Title                 \t%-25s
Description           \t%-25s 
Type                  \t%-25s
Issued                \t%-25s
Updated               \t%-25s
Version               \t%-25s
Release               \t%-25s
Status                \t%-25s
Packages Effected     \t%-25s
Reboot Suggested      \t%-25s
References            \t%-25s
"""

DISTRO_LIST = """
Id                    \t%-25s
Description           \t%-25s 
URL                   \t%-25s
"""

DISTRO_INFO = """
Id                    \t%-25s
Description           \t%-25s 
URL                   \t%-25s
Files                 \t%-25s
relativepath          \t%-25s
"""

# The quotes are intentionally placed odd on the consumer history constants to
# allow additional details to be concatenated on to the base information. It looks
# ugly in code but makes the actual CLI output much cleaner. So be careful when
# dorking with these.
CONSUMER_HISTORY_ENTRY = """
Event Type            \t%-25s
Timestamp             \t%-25s
Originator            \t%-25s"""

CONSUMER_HISTORY_REPO = """Repo ID               \t%-25s"""

CONSUMER_HISTORY_PACKAGES = """Packages"""

CONSUMER_HISTORY_EVENT_TYPES = {
    'consumer_created' : 'Consumer Created',
    'consumer_deleted' : 'Consumer Deleted',
    'repo_bound' : 'Repo Bound',
    'repo_unbound' : 'Repo Unbound',
    'package_installed' : 'Package Installed',
    'package_uninstalled' : 'Package Uninstalled',
}

CONSUMER_WRONG_HOST_ERROR = \
"""ERROR: The server hostname you have configured in /etc/pulp/ does not match the
hostname returned from the Pulp server you are connecting to.

You have: [%s] configured but received: [%s] from the server.

Either correct the host in /etc/pulp/ or specify --server=%s"""

CDS_INFO = '''
Name                \t%-25s
Hostname            \t%-25s
Description         \t%-25s
Repos               \t%-25s
Last Sync           \t%-25s
Status:
   Responding       \t%-25s
   Last Heartbeat   \t%-25s
'''

CDS_HISTORY_ENTRY = '''
Event Type          \t%-25s
Timestamp           \t%-25s
Originator          \t%-25s'''

CDS_HISTORY_ENTRY_ERROR = '''Exception           \t%-25s'''

CDS_HISTORY_EVENT_TYPES = {
    'registered' : 'Registered',
    'unregistered' : 'Unregistered',
    'sync_started' : 'Sync Started',
    'sync_finished' : 'Sync Finished',
    'repo_associated' : 'Repo Associated',
    'repo_unassociated' : 'Repo Unassociated',
}

CDS_SYNC_DETAILS = '''
State               \t%-25s
Start Time          \t%-25s
Finish Time         \t%-25s'''


UNAVAILABLE = '''
The following consumers appear to be unavailable.
You may continue with the understanding that your request
will not complete until all consumers have processed the request.

Unavailable Consumers
------------------------------
'''

METADATA_STATUS = """
Task Id          \t%-25s
Status           \t%-25s
Start Time       \t%-25s
Finish Time      \t%-25s
"""
