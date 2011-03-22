# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

from logging import getLogger

from gofer.messaging import Queue
from gofer.messaging.async import ReplyConsumer, Listener

from pulp.server.agent import Agent
from pulp.server.config import config
from pulp.server.tasking.queue.fifo import FIFOTaskQueue
from pulp.server.tasking.task import Task, AsyncTask


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
    if _queue.enqueue(task, unique):
        return task
    return None


def run_async(method, args, kwargs, timeout=None, unique=True, task_type=None):
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
    if not task_type:
        task_type = Task
    task = task_type(method, args, kwargs, timeout)
    return enqueue(task, unique)


def find_async(**kwargs):
    return _queue.find(**kwargs)


def cancel_async(task):
    return _queue.cancel(task)

# async system initialization/finalization ------------------------------------

def initialize():
    """
    Explicitly start-up the asynchronous sub-system
    """
    global _queue
    _queue = FIFOTaskQueue()


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
    @ivar __id: The agent (consumer) id.  Or, list of IDs.
    @type __id: (str|[str,..])
    """
    def __init__(self, id):
        """
        @param id: The agent ID.  Or, list of IDs.
        @type id: (str|[str,..])
        """
        self.__id = id

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
            return RemoteClass(self.__id, name)


class RemoteClass:
    """
    Represents a I{remote} class.
    @ivar __id: The agent (consumer) id.
    @type __id: str
    @ivar __name: The remote class name.
    @type __name: str
    @ivar __taskid: The correlated taskid.
    @type __taskid: str
    """
    def __init__(self, id, name):
        """
        @param id: The agent (consumer) id.
        @type id: str
        @param name: The remote class name.
        @type name: str
        """
        self.__id = id
        self.__name = name
        self.__taskid = 0

    def __call__(self, task):
        """
        Mock constructor.
        @param task: The associated task.
        @type task: L{Task}
        @return: self
        @rtype: L{AsyncClass}
        """
        self.taskid = task.id
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
        return RemoteMethod(self.__id, self.__name, name, self.taskid)


class RemoteMethod:
    """
    Represents a I{remote} method.
    @cvar CTAG: The RMI correlation tag.
    @type CTAG: str
    @ivar id: The consumer id.
    @type id: str
    @ivar im_class: The remote class.
    @type im_class: classobj
    @ivar name: The method name.
    @type name: str
    @ivar cb: The completed callback (module,class).
    @type cb: tuple
    @ivar taskid: The associated task ID.
    @type taskid: str
    """

    CTAG = 'asynctaskreplyqueue'

    def __init__(self, id, classname, name, taskid):
        """
        @param id: The consumer (agent) id.
        @type id: str
        @param classname: The remote object class name.
        @type classname: str
        @param name: The remote method name.
        @type name: str
        @param taskid: The associated task ID.
        @type taskid: str
        """
        self.id = id
        self.classname = classname
        self.name = name
        self.taskid = taskid

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
        url = config.get('messaging', 'url')
        agent = Agent(
            self.id,
            url=url,
            any=self.taskid,
            ctag=self.CTAG)
        classobj = getattr(agent, self.classname)
        method = getattr(classobj, self.name)
        return method(*args, **kwargs)


class ReplyHandler(Listener):
    """
    The async RMI reply handler.
    @ivar consumer: The reply consumer.
    @type consumer: L{ReplyConsumer}
    """
    def __init__(self):
        ctag = RemoteMethod.CTAG
        url = config.get('messaging', 'url')
        queue = Queue(ctag)
        self.consumer = ReplyConsumer(queue, url=url)

    def start(self):
        self.consumer.start(self)
        log.info('Task reply handler, started.')

    def succeeded(self, reply):
        log.info('Task RMI (succeeded)\n%s', reply)
        taskid = reply.any
        task = _queue.find(id=taskid)
        if task:
            sn = reply.sn
            result = reply.retval
            task[0].succeeded(sn, result)
        else:
            log.warn('Task (%s), not found', taskid)

    def failed(self, reply):
        log.info('Task RMI (failed)\n%s', reply)
        taskid = reply.any
        task = _queue.find(id=taskid)
        if task:
            sn = reply.sn
            exception = reply.exval,
            tb = repr(exception)
            task[0].failed(sn, exception, tb)
        else:
            log.warn('Task (%s), not found', taskid)

    def status(self, reply):
        pass


class AgentTask(AsyncTask):
    """
    Task represents an async task involving an RMI to the agent.
    """
    def succeeded(self, sn, result):
        """
        The RMI succeeded.
        @param sn: The RMI serial #.
        @type sn: uuid
        @param result: The RMI returned value.
        @type result: object
        """
        AsyncTask.succeeded(self, result)

    def failed(self, sn, exception, tb=None):
        """
        @param sn: The RMI serial #.
        @type sn: uuid
        @param exception: The RMI raised exception.
        @type exception: Exception
        @param tb: The exception traceback.
        @type tb: list
        """
        AsyncTask.failed(self, exception, tb=tb)

    def enqueue(self, unique=False):
        """
        Enqueue the task.
        @param unique: The unique flag.
        @type unique: bool
        """
        if _queue.enqueue(self, unique):
            return self

