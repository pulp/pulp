# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


# --- plugins ----------------------------------------------------------------


HTTP_DISTRIBUTOR = 'nodes_http_distributor'
HTTP_IMPORTER = 'nodes_http_importer'

ALL_IMPORTERS = [HTTP_IMPORTER]
ALL_DISTRIBUTORS = [HTTP_DISTRIBUTOR]


# --- strategies -------------------------------------------------------------

ADDITIVE_STRATEGY = 'additive'
MIRROR_STRATEGY = 'mirror'
STRATEGIES = [ADDITIVE_STRATEGY, MIRROR_STRATEGY]
DEFAULT_STRATEGY = ADDITIVE_STRATEGY

NODE_SCOPE = 'node'
REPOSITORY_SCOPE = 'repository'
SCOPES = [NODE_SCOPE, REPOSITORY_SCOPE]


# --- keywords ---------------------------------------------------------------

STRATEGY_KEYWORD = 'strategy'
PROTOCOL_KEYWORD = 'protocol'
MANIFEST_URL_KEYWORD = 'manifest_url'
PURGE_ORPHANS_KEYWORD = 'purge_orphans'

MAX_DOWNLOAD_BANDWIDTH_KEYWORD = 'max_download_bandwidth'
MAX_DOWNLOAD_CONCURRENCY_KEYWORD = 'max_download_concurrency'

SKIP_CONTENT_UPDATE_KEYWORD = 'skip_content_update'


# --- unit/publishing --------------------------------------------------------

TYPE_ID = 'type_id'
UNIT_KEY = 'unit_key'
BASE_URL = 'base_url'
STORAGE_PATH = 'storage_path'
RELATIVE_PATH = 'relative_path'
FILE_SIZE = 'size'
TARBALL_PATH = 'tgz_path'
LAST_UPDATED = 'last_updated'


# --- consumer notes ---------------------------------------------------------

NODE_NOTE_KEY = '_child-node'
STRATEGY_NOTE_KEY = '_node-update-strategy'


# --- settings ---------------------------------------------------------------

DEFAULT_DOWNLOAD_CONCURRENCY = 20


# --- profiling --------------------------------------------------------------

PROFILER_ID = 'node'
PARENT_SETTINGS = 'parent_settings'
NODE_CERTIFICATE = 'node_certificate'
HOST = 'host'
PORT = 'port'
