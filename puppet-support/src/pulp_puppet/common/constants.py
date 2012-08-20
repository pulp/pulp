# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains constants that are global across the entire puppet plugin. Eventually,
this will be pulled into a common dependency across all of the puppet
support plugins (importers, distributors, extensions).
"""

# -- ids ----------------------------------------------------------------------

# ID used to refer to the puppet importer
IMPORTER_ID_PUPPET = 'puppet_importer'

# ID used to refer to the puppet distributor
DISTRIBUTOR_ID_PUPPET = 'puppet_distributor'

# ID of the puppet module type definition (must match what's in puppet.json)
TYPE_PUPPET_MODULE = 'puppet_module'

# -- storage and hosting ------------------------------------------------------

# Name of the hosted file describing the contents of the repository
REPO_METADATA_FILENAME = 'modules.json'

# File name inside of a module where its metadata is found
MODULE_METADATA_FILENAME = 'metadata.json'

# Location in the repository where a module will be hosted
# Substitutions: author first character, author
HOSTED_MODULE_FILE_RELATIVE_PATH = 'system/releases/%s/%s/'

# Name template for a module
# Substitutions: author, name, version
MODULE_FILENAME = '%s-%s-%s.tar.gz'

# Location in Pulp where modules will be stored (the filename includes all
# of the uniqueness of the module, so we can keep this flat)
# Substitutions: filename
STORAGE_MODULE_RELATIVE_PATH = '%s'

# -- progress states ----------------------------------------------------------

STATE_NOT_STARTED = 'not-started'
STATE_RUNNING = 'running'
STATE_SUCCESS = 'success'
STATE_FAILED = 'failed'

INCOMPLETE_STATES = (STATE_NOT_STARTED, STATE_RUNNING, STATE_FAILED)

# -- importer configuration keys ----------------------------------------------

# Location from which to sync modules
CONFIG_FEED = 'feed'

# List of queries to run on the feed
CONFIG_QUERIES = 'queries'

# Whether or not to remove modules that were previously synchronized but were
# not on a subsequent sync
CONFIG_REMOVE_MISSING = 'remove_missing'
DEFAULT_REMOVE_MISSING = False

# -- distributor configuration keys -------------------------------------------

# Controls if modules will be served over HTTP
CONFIG_SERVE_HTTP = 'serve_http'
DEFAULT_SERVE_HTTP = True

# Controls if modules will be served over HTTP
CONFIG_SERVE_HTTPS = 'serve_https'
DEFAULT_SERVE_HTTPS = False
