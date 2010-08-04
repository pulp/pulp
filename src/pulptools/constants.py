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
Label              \t%-25s
Name               \t%-25s
Feed               \t%-25s
Arch               \t%-25s
Sync Schedule      \t%-25s
Packages           \t%-25s
"""

AVAILABLE_CONSUMER_GROUP_INFO="""
Id                 \t%-25s
Description        \t%-25s
Consumer ids       \t%-25s
"""


AVAILABLE_CONSUMER_INFO="""
Id                 \t%-25s
Description        \t%-25s
Subscribed Repos   \t%-25s
Profile            \t%-25s
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


AVAILABLE_USERS_LIST = """
Login :               \t%-25s    
Name  :                \t%-25s
"""

ERRATA_INFO="""
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
References            \t%-25s
"""
