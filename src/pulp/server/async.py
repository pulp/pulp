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

import traceback
from gettext import gettext as _
from logging import getLogger


from pulp.server import config
from pulp.server.agent import Agent
from pulp.server.db.model.persistence import TaskSnapshot
from pulp.server.tasking.exception import (
    NonUniqueTaskException, DuplicateSnapshotError, UnscheduledTaskException)
from pulp.server.tasking.task import Task, AsyncTask
from pulp.server.tasking.taskqueue.queue import TaskQueue
from pulp.server.tasking.taskqueue.storage import SnapshotStorage
from gofer.rmi.async import WatchDog



log = getLogger(__name__)

# async execution queue -------------------------------------------------------

_queue = None

# async api -------------------------------------------------------------------

def enqueue(task, unique=True):
    """
    Enqueue a task.
    @param task: The task to enqueue.
    @type task: L{Task}
    @param unique: whether or not to make sure the task isn't already being run
    @type unique: bool
    """
    # circular imports...
    from pulp.server.auth.authorization import (
        GrantPermissionsForTask, RevokePermissionsForTask)
    # make sure to set the appropriate permissions for the task
    grant = GrantPermissionsForTask()
    revoke = RevokePermissionsForTask()
    task.add_enqueue_hook(grant)
    task.add_dequeue_hook(revoke)
    try:
        _queue.enqueue(task, unique)
    except NonUniqueTaskException, e:
        log.error(e.args[0])
        task.remove_enqueue_hook(grant)
        task.remove_dequeue_hook(revoke)
        return None
    except DuplicateSnapshotError, e:
        log.error(traceback.format_exc())
        task.remove_enqueue_hook(grant)
        task.remove_dequeue_hook(revoke)
        return None
    except UnscheduledTaskException:
        log.info(traceback.format_exc())
        task.remove_enqueue_hook(grant)
        task.remove_dequeue_hook(revoke)
        return None
    return task


def run_async(method, args=None, kwargs=None, timeout=None, unique=True, task_type=None):
    """
    Make a python call asynchronously.
    @type method: callable
    @param method: method to call asynchronously
    @type args: list or tuple
    @param args: list of positional arguments for method
    @type kwargs: dict
    @param kwargs: key word arguements for method
    @type timeout: datetime.timedelta instance
    @param timeout: maximum length of time to let method run before interrupting it
    @type unique: bool
    @param unique: whether or not to make sure the task isn't already being run
    @rtype: L{Task} instance or None
    @return: L{Task} instance on success, None otherwise
    """
    args = args or []
    kwargs = kwargs or {}
    if not task_type:
        task_type = Task
    task = task_type(method, args, kwargs, timeout)
    return enqueue(task, unique)


def cancel_async(task):
    return _queue.cancel(task)


def reschedule_async(task, scheduler):
    return _queue.reschedule(task, scheduler)


def find_async(**kwargs):
    return _queue.find(**kwargs)


def remove_async(task):
    return _queue.remove(task)


def drop_complete_async(task):
    return _queue.drop_complete(task)


def waiting_async():
    return _queue.waiting_tasks()


def running_async():
    return _queue.running_tasks()


def incomplete_async():
    return _queue.incomplete_tasks()


def complete_async():
    return _queue.complete_tasks()


def all_async():
    return _queue.all_tasks()

# async system initialization/finalization ------------------------------------

def _configured_schedule_threshold():
    value = config.config.get('tasking', 'schedule_threshold')
    return config.parse_time_delta(value)


def _load_persisted_tasks():
    assert _queue is not None
    collection = TaskSnapshot.get_collection()
    tasks = []
    snapshot_ids = []
    for snapshot in collection.find():
        snapshot_ids.append(snapshot['_id'])
        task = TaskSnapshot(snapshot).to_task()
        tasks.append(task)
        log.info(_('Loaded Task from database: %s') % str(task))
    for id in snapshot_ids:
        last_error = collection.remove({'_id': id}, safe=True)
        if not last_error.get('ok', False):
            raise Exception(repr(last_error))
    for task in tasks:
        enqueue(task)


def initialize():
    """
    Explicitly start-up the asynchronous sub-system
    """
    global _queue
    concurrency_threshold = config.config.getint('tasking', 'concurrency_threshold')
    if config.config.has_option('tasking', 'max_concurrent'):
        log.warn(_('The [tasking] max_concurrent configuration option is depricated and will be removed. Use the [tasking] concurrency_threshold option instead'))
        concurrency_threshold = config.config.getint('tasking', 'max_concurrent')
    failure_threshold = config.config.getint('tasking', 'failure_threshold')
    if failure_threshold < 1:
        failure_threshold = None
    schedule_threshold = _configured_schedule_threshold()
    _queue = TaskQueue(max_concurrency=concurrency_threshold,
                       failure_threshold=failure_threshold,
                       schedule_threshold=schedule_threshold,
                       storage=SnapshotStorage(),
                       dispatch_interval=5)
    _load_persisted_tasks()


def finalize():
    """
    Explicitly shut-down the asynchronous sub-system
    """
    global _queue
    q = _queue
    _queue = None
    del q

# agent classes ---------------------------------------------------------------

class AsyncAgent:
    """
    Represents the I{remote} agent.
    @ivar __id: The agent (consumer) id.
    @type __id: str
    @ivar __secret: The shared secret.
    @type __secret: str
    @ivar __options: Additional gofer options.
    @type __options: dict
    """

    def __init__(self, id, secret, **options):
        """
        @param id: The agent ID.
        @type id: str
        @param secret: The shared secret.
        @type secret: str
        @param options: Additional gofer options.
        @type options: dict
        """
        self.__id = id
        self.__secret = secret
        self.__options = options

    def __getattr__(self, name):
        """
        @param name: the remote class name.
        @type name: str
        @return: A wrapper object for the remote class.
        @rtype: L{AsyncClass}
        """
        if name.startswith('__'):
            return self.__dict__[name]
        else:
            return RemoteClass(
                self.__id,
                self.__secret,
                self.__options,
                name)


class RemoteClass:
    """
    Represents a I{remote} class.
    @ivar __id: The agent (consumer) id.
    @type __id: str
    @ivar __secret: The shared secret.
    @type __secret: str
    @ivar __options: Additional gofer options.
    @type __options: dict
    @ivar __cntr: Remote class constructor arguments.
    @type __cntr: tuple ([],{})
    @ivar __name: The remote class name.
    @type __name: str
    @ivar __taskid: The correlated taskid.
    @type __taskid: str
    @ivar __called: Tracks when mock constructor called.
    @type __called: bool
    """

    def __init__(self, id, secret, options, name):
        """
        @param id: The agent (consumer) id.
        @type id: str
        @param secret: The shared secret.
        @type secret: str
        @param options: Additional gofer options.
        @type options: dict
        @param name: The remote class name.
        @type name: str
        """
        self.__id = id
        self.__secret = secret
        self.__options = options
        self.__cntr = None
        self.__name = name
        self.__taskid = 0
        self.__called = False

    def __call__(self, *args, **options):
        """
        Mock constructor.
        @param task: The associated task.
        @type task: L{Task}
        @return: self
        @rtype: L{AsyncClass}
        """
        if self.__called:
            self.__cntr = (args, options)
            return self
        task = args[0]
        self.taskid = task.id
        d = dict(self.__options)
        d.update(options)
        self.__options = d
        self.__called = True
        return self

    def __getattr__(self, name):
        """
        Get the method.
        @param name: The remote class method name.
        @type name: str
        @return: A remote method wrapper.
        @rtype: L{RemoteMethod}
        """
        if name.startswith('__'):
            return self.__dict__[name]
        return RemoteMethod(
            self.__id,
            self.__secret,
            self.__name,
            self.__cntr,
            self.__options,
            self.taskid,
            name)


class RemoteMethod:
    """
    Represents a I{remote} method.
    @cvar CTAG: The RMI correlation tag.
    @type CTAG: str
    @ivar id: The consumer id.
    @type id: str
    @ivar secret: The shared secret.
    @type secret: str
    @ivar classname: The remote class.
    @type classname: classobj
    @ivar cntr: Remote class constructor arguments.
    @type cntr: tuple ([],{})
    @ivar options: Additional gofer options.
    @type options: dict
    @ivar taskid: The associated task ID.
    @type taskid: str
    @ivar name: The method name.
    @type name: str
    """

    CTAG = 'pulp.task'

    def __init__(self, id, secret, classname, cntr, options, taskid, name):
        """
        @param id: The consumer (agent) id.
        @type id: str
        @param secret: The shared secret.
        @type secret: str
        @param classname: The remote object class name.
        @type classname: str
        @param cntr: Remote class constructor arguments.
        @type cntr: tuple ([],{})
        @param options: Additional gofer options.
        @type options: dict
        @param taskid: The associated task ID.
        @type taskid: str
        @param name: The remote method name.
        @type name: str
        """
        self.id = id
        self.secret = secret
        self.classname = classname
        self.cntr = cntr
        self.options = options
        self.taskid = taskid
        self.name = name

    def __call__(self, *args, **kwargs):
        """
        On invocation, perform the async RMI to the agent.
        @param args: Invocation args.
        @type args: list
        @param kwargs: keyword invocation args.
        @type kwargs: dict
        @return: Whatever is returned by the async RMI.
        @rtype: object
        """
        url = config.config.get('messaging', 'url')
        watchdog = WatchDog(url=url)
        agent = Agent(
            self.id,
            url=url,
            secret=self.secret,
            any=self.taskid,
            ctag=self.CTAG,
            watchdog=watchdog,
            **self.options)
        classobj = getattr(agent, self.classname)()
        if isinstance(self.cntr, tuple):
            classobj(*self.cntr[0], **self.cntr[1])
        method = getattr(classobj, self.name)
        return method(*args, **kwargs)
