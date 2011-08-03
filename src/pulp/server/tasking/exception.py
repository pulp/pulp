# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class TaskingException(Exception):
    """
    Base exception class for tasking.
    """
    pass

# task exceptions --------------------------------------------------------------

class TaskThreadException(TaskingException):
    """
    Base class for task-specific exceptions to be raised in a task thread.
    """
    pass


class TimeoutException(TaskThreadException):
    """
    Exception to interrupt a task with a time out.
    """
    pass


class CancelException(TaskThreadException):
    """
    Exception to interrupt a task with a cancellation.
    """
    pass


class ConflictingOperationException(TaskThreadException):
    """
    Exception to signify a task couldn't run due to a conflict,
    possibly a previous operation was still in progress
    """
    pass


class TaskThreadInterruptionError(TaskThreadException):
    """
    Exception class used to flag and catch exceptions thrown by this api.
    """
    pass


class TaskThreadStateError(TaskThreadException):
    '''
    Exception class used to indicate one or more child threads is in a state
    that cannot currently be canceled.
    '''
    pass

# task queue exceptions --------------------------------------------------------

class UnscheduledTaskException(TaskingException):
    """
    Raised when a task calls schedule, but can no longer be scheduled.
    """
    pass


class NonUniqueTaskException(TaskingException):
    """
    Raised when a non-unique task is enqueued and the unique flag is True.
    """
    pass

# task storage exceptions ------------------------------------------------------

class SnapshotFailure(TaskingException):
    """
    Raised when a task snapshot fails.
    """
    pass


class DuplicateSnapshotError(TaskingException):
    """
    Raised when more than one snapshot is created for the same task.
    """
    pass
