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

import time
from gettext import gettext as _
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand
from pulp.bindings.exceptions import NotFoundException

# -- framework hook -----------------------------------------------------------

def initialize(context):
    consumer_section = context.cli.find_section('consumer')
    consumer_section.add_subsection(ContentSection(context))
    consumer_section.remove_subsection('content')

# -- constants --------------------------------------------------------

TYPE_ID = 'rpm'

# -- sections --------------------------------------------------------


class ContentSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(
            self,
            'package',
            _('package installation management'))
        for Command in (InstallContent, UpdateContent, UninstallContent):
            command = Command(context)
            command.create_option(
                '--id',
                _('identifies the consumer'),
                required=True)
            command.create_flag(
                '--no-commit',
                _('transaction not committed'))
            command.create_flag(
                '--reboot',
                _('reboot after successful transaction'))
            self.add_command(command)


class PollingCommand(PulpCliCommand):

    def process(self, id, task):
        prompt = self.context.prompt
        m = 'This command may be exited via CTRL+C without affecting the install.'
        prompt.render_paragraph(_(m))
        try:
            task = self.poll(task)
            if task.was_successful():
                self.succeeded(id, task)
                return
            if task.was_failure():
                self.failed(id, task)
                return
            if task.was_cancelled():
                self.cancelled(id, task)
                return
        except KeyboardInterrupt:
            # graceful interrupt
            pass

    def poll(self, task):
        server = self.context.server
        cfg = self.context.config
        spinner = self.context.prompt.create_spinner()
        interval = float(cfg['output']['poll_frequency_in_seconds'])
        while not task.is_completed():
            if task.is_waiting():
                spinner.next(_('Waiting to begin'))
            else:
                spinner.next()
            time.sleep(interval)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
        return task

    def rejected(self, task):
        rejected = task.is_rejected()
        if rejected:
            prompt = self.context.prompt
            msg = 'The request was rejected by the server'
            prompt.render_failure_message(_(msg))
            msg = 'This is likely due to an impending delete request for the consumer.'
            prompt.render_failure_message(_(msg))
        return rejected

    def postponed(self, task):
        postponed = task.is_postponed()
        if postponed:
            msg  = \
                'The request to update content was accepted but postponed ' \
                'due to one or more previous requests against the consumer.' \
                ' This request will take place at the earliest possible time.'
            self.context.prompt.render_paragraph(_(msg))
        return postponed

    def failed(self, id, task):
        prompt = self.context.prompt
        msg = 'Request Failed'
        prompt.render_failure_message(_(msg))
        prompt.render_failure_message(task.exception)

    def cancelled(self, id, response):
        prompt = self.context.prompt
        prompt.render_failure_message('Request Cancelled')


class InstallContent(PollingCommand):

    def __init__(self, context):
        PollingCommand.__init__(
            self,
            'install',
            _('install packages'),
            self.run)
        self.create_option(
            '--name',
            _('package name; may repeat for multiple packages'),
            required=True,
            allow_multiple=True,
            aliases=['-n'])
        self.create_flag(
            '--import-keys',
            _('import GPG keys as needed'))
        self.context = context

    def run(self, **kwargs):
        id = kwargs['id']
        apply = (not kwargs['no-commit'])
        importkeys = kwargs['import-keys']
        reboot = kwargs['reboot']
        units = []
        options = dict(
            apply=apply,
            importkeys=importkeys,
            reboot=reboot,)
        for name in kwargs['name']:
            unit_key = dict(name=name)
            unit = dict(type_id=TYPE_ID, unit_key=unit_key)
            units.append(unit)
        self.install(id, units, options)

    def install(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        try:
            response = server.consumer_content.install(id, units=units, options=options)
            task = response.response_body
            msg = _('Install task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # reported as failed
        if not task.result['status']:
            msg = 'Install failed'
            details = task.result['details'][TYPE_ID]['details']
            prompt.render_failure_message(_(msg))
            prompt.render_failure_message(details['message'])
            return
        msg = 'Install Succeeded'
        prompt.render_success_message(_(msg))
        # reported as succeeded
        details = task.result['details'][TYPE_ID]['details']
        filter = ['name', 'version', 'arch', 'repoid']
        resolved = details['resolved']
        if resolved:
            prompt.render_title('Installed')
            prompt.render_document_list(
                resolved,
                order=filter,
                filters=filter)
        else:
            msg = 'Packages already installed'
            prompt.render_success_message(_(msg))
        deps = details['deps']
        if deps:
            prompt.render_title('Installed for dependency')
            prompt.render_document_list(
                deps,
                order=filter,
                filters=filter)


class UpdateContent(PollingCommand):

    def __init__(self, context):
        PollingCommand.__init__(
            self,
            'update',
            _('update (installed) packages'),
            self.run)
        self.create_option(
            '--name',
            _('package name; may repeat for multiple packages'),
            required=False,
            allow_multiple=True,
            aliases=['-n'])
        self.create_flag(
            '--import-keys',
            _('import GPG keys as needed'))
        self.create_flag(
            '--all',
            _('update all packages'),
            aliases=['-a'])
        self.context = context

    def run(self, **kwargs):
        id = kwargs['id']
        all = kwargs['all']
        names = kwargs['name']
        apply = (not kwargs['no-commit'])
        importkeys = kwargs['import-keys']
        reboot = kwargs['reboot']
        units = []
        options = dict(
            all=all,
            apply=apply,
            importkeys=importkeys,
            reboot=reboot,)
        if all: # ALL
            unit = dict(type_id=TYPE_ID, unit_key=None)
            self.update(id, [unit], options)
            return
        if names is None:
            names = []
        for name in names:
            unit_key = dict(name=name)
            unit = dict(type_id=TYPE_ID, unit_key=unit_key)
            units.append(unit)
        self.update(id, units, options)

    def update(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        if not units:
            msg = 'No packages specified'
            prompt.render_failure_message(_(msg))
            return
        try:
            response = server.consumer_content.update(id, units=units, options=options)
            task = response.response_body
            msg = _('Update task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # reported as failed
        if not task.result['status']:
            msg = 'Install failed'
            details = task.result['details'][TYPE_ID]['details']
            prompt.render_failure_message(_(msg))
            prompt.render_failure_message(details['message'])
            return
        msg = 'Install Succeeded'
        prompt.render_success_message(_(msg))
        # reported as succeeded
        details = task.result['details'][TYPE_ID]['details']
        filter = ['name', 'version', 'arch', 'repoid']
        resolved = details['resolved']
        if resolved:
            prompt.render_title('Updated')
            prompt.render_document_list(
                resolved,
                order=filter,
                filters=filter)
        else:
            msg = 'No updates needed'
            prompt.render_success_message(_(msg))
        deps = details['deps']
        if deps:
            prompt.render_title('Installed for dependency')
            prompt.render_document_list(
                deps,
                order=filter,
                filters=filter)


class UninstallContent(PollingCommand):

    def __init__(self, context):
        PollingCommand.__init__(
            self,
            'uninstall',
            _('uninstall packages'),
            self.run)
        self.create_option(
            '--name',
            _('package name; may repeat for multiple packages'),
            required=True,
            allow_multiple=True,
            aliases=['-n'])
        self.context = context

    def run(self, **kwargs):
        id = kwargs['id']
        apply = (not kwargs['no-commit'])
        reboot = kwargs['reboot']
        units = []
        options = dict(
            apply=apply,
            reboot=reboot,)
        for name in kwargs['name']:
            unit_key = dict(name=name)
            unit = dict(type_id=TYPE_ID, unit_key=unit_key)
            units.append(unit)
        self.uninstall(id, units, options)

    def uninstall(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        try:
            response = server.consumer_content.uninstall(id, units=units, options=options)
            task = response.response_body
            msg = _('Uninstall task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # reported as failed
        if not task.result['status']:
            msg = 'Install Failed'
            details = task.result['details'][TYPE_ID]['details']
            prompt.render_failure_message(_(msg))
            prompt.render_failure_message(details['message'])
            return
        msg = 'Install Succeeded'
        prompt.render_success_message(_(msg))
        # reported as succeeded
        details = task.result['details'][TYPE_ID]['details']
        filter = ['name', 'version', 'arch', 'repoid']
        resolved = details['resolved']
        if resolved:
            prompt.render_title('Uninstalled')
            prompt.render_document_list(
                resolved,
                order=filter,
                filters=filter)
        else:
            msg = 'No matching packages found to uninstall'
            prompt.render_success_message(_(msg))
        deps = details['deps']
        if deps:
            prompt.render_title('Uninstalled for dependency')
            prompt.render_document_list(
                deps,
                order=filter,
                filters=filter)
