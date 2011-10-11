# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import atexit
import logging
from ConfigParser import SafeConfigParser

import web

from pulp.server import config # automatically loads config
from pulp.server import logs
from pulp.server.db import connection as db_connection

# We need to read the config, start the logging, and initialize the db
#connection prior to any other imports, since some of the imports will invoke
# setup methods
logs.start_logging()
db_connection.initialize()

from pulp.client.core.utils import parse_interval_schedule
from pulp.common.dateutils import (parse_iso8601_interval,
    parse_iso8601_duration, format_iso8601_duration,
    format_iso8601_datetime)

from pulp.server import async
from pulp.server import auditing
from pulp.server.agent import HeartbeatListener
from pulp.server.api import consumer_history
from pulp.server.api import scheduled_sync
from pulp.server.api import cds, repo
from pulp.server.async import ReplyHandler
from pulp.server.auth.admin import ensure_admin
from pulp.server.auth.authorization import ensure_builtin_roles
from pulp.server.db.version import check_version
from pulp.server.debugging import StacktraceDumper
from pulp.server.event.dispatcher import EventDispatcher
from pulp.server.webservices.controllers import (
    audit, cds, consumergroups, consumers, content, distribution, errata,
    filters, orphaned, packages, permissions, repositories, roles, services,
    tasks, users)

from gofer.messaging.broker import Broker

# conatants and application globals --------------------------------------------

URLS = (
    # alphabetical order, please
    # default version (currently 1) api
    '/cds', cds.application,
    '/consumergroups', consumergroups.application,
    '/consumers', consumers.application,
    '/content', content.application,
    '/distribution', distribution.application,
    '/errata', errata.application,
    '/events', audit.application,
    '/filters', filters.application,
    '/orphaned', orphaned.application,
    '/packages', packages.application,
    '/permissions', permissions.application,
    '/repositories', repositories.application,
    '/roles', roles.application,
    '/services', services.application,
    '/tasks', tasks.application,
    '/users', users.application,
)

_IS_INITIALIZED = False

BROKER = None
DISPATCHER = None
REPLY_HANDLER = None
HEARTBEAT_LISTENER = None
STACK_TRACER = None

# initialization ---------------------------------------------------------------

def _update_sync_schedules():
    """
    Read what the sync schedules for repositories and cds's have been set as
    from the rhui tools config file and update them if necessary.

    This isn't ideal, since these values are set in a different config file
    for a client tool, but barring a large documentation change, this is a
    stop gap measure to make sure these settings get updated in pulp which
    previously wasn't happening at all before.
    """
    repo_api = repo.RepoApi()
    cds_api = cds.CdsApi()

    tools_config = SafeConfigParser()
    tools_config.read("/etc/rhui/rhui-tools.conf")

    # Format the sync frequencies, then feed it through and back out the
    # datetime library to normalize it.  This accounts for differences like
    # 30H vs 1D6H.
    repo_sync_freq_iso = "PT%sH" % tools_config.get('rhui', 'repo_sync_frequency')
    repo_sync_freq = parse_iso8601_duration(repo_sync_freq_iso)
    repo_sync_freq_iso = format_iso8601_duration(repo_sync_freq)
    cds_sync_freq_iso = "PT%sH" % tools_config.get('rhui', 'cds_sync_frequency')
    cds_sync_freq = parse_iso8601_duration(cds_sync_freq_iso)
    cds_sync_freq_iso = format_iso8601_duration(cds_sync_freq)

    repos_list = repo_api.repositories()
    cds_list = cds_api.list()

    def _sync_schedule_param(sync_schedule, new_sync_freq_iso):
        interval, start, runs = parse_iso8601_interval(sync_schedule)
        interval_iso = format_iso8601_duration(interval)
        param = {}
        if interval_iso != new_sync_freq_iso:
            start_iso = format_iso8601_datetime(start)
            runs = None
            param["sync_schedule"] = parse_interval_schedule(new_sync_freq_iso,
                start_iso, runs)
            return param
        else:
            return None

    for _repo in repos_list:
        param = _sync_schedule_param(_repo["sync_schedule"], repo_sync_freq_iso)
        if param:
            repo_api.update(_repo["id"], param)
        else:
            continue

    for _cds in cds_list:
        param = _sync_schedule_param(_cds["sync_schedule"], cds_sync_freq_iso)
        if param:
            cds_api.update(_cds["id"], param)
        else:
            continue

def _initialize_pulp():
    # XXX ORDERING COUNTS
    # This initialization order is very sensitive, and each touches a number of
    # sub-systems in pulp. If you get this wrong, you will have pulp tripping
    # over itself on start up. If you do not know where to add something, ASK!
    global _IS_INITIALIZED, BROKER, DISPATCHER, REPLY_HANDLER, \
           HEARTBEAT_LISTENER, STACK_TRACER
    if _IS_INITIALIZED:
        return
    _IS_INITIALIZED = True
    # check our db version and other support
    check_version()
    # ensure necessary infrastructure
    ensure_builtin_roles()
    ensure_admin()
    # clean up previous runs, if needed
    repo.clear_sync_in_progress_flags()
    # messaging
    url = config.config.get('messaging', 'url')
    # amqp broker
    BROKER = Broker(url)
    BROKER.cacert = config.config.get('messaging', 'cacert')
    BROKER.clientcert = config.config.get('messaging', 'clientcert')
    # event dispatcher
    if config.config.getboolean('events', 'recv_enabled'):
        DISPATCHER = EventDispatcher()
        DISPATCHER.start()
    # async task reply handler
    REPLY_HANDLER = ReplyHandler(url)
    # agent heartbeat listener
    HEARTBEAT_LISTENER = HeartbeatListener(url)
    HEARTBEAT_LISTENER.start()
    # async subsystem and schedules tasks
    async.initialize()
    # pulp finalization methods, registered via 'atexit'
    atexit.register(async.finalize)
    # setup debugging, if configured
    if config.config.getboolean('server', 'debugging_mode'):
        STACK_TRACER = StacktraceDumper()
        STACK_TRACER.start()
    # setup recurring tasks
    auditing.init_culling_task()
    consumer_history.init_culling_task()
    _update_sync_schedules()
    scheduled_sync.init_scheduled_syncs()



def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the web.py framework.
    @return: wsgi application callable
    """
    application = web.subdir_application(URLS)
    _initialize_pulp()
    return application.wsgifunc()
