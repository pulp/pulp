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

import os
from M2Crypto import X509
from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, PulpCliOption, PulpCliFlag, UnknownArgsParser
from pulp.bindings.exceptions import NotFoundException

from pulp.common.bundle import Bundle
from pulp.common.capabilities import AgentCapabilities


# -- framework hook -----------------------------------------------------------

def initialize(context):
    context.cli.add_section(ConsumerSection(context))
    
# -- common exceptions --------------------------------------------------------

class InvalidConfig(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

# -- sections -----------------------------------------------------------------

class ConsumerSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'consumer', 'consumer lifecycle (register, unregister, update, etc.) commands')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Common Options
        id_option = PulpCliOption('--id', 'uniquely identifies the consumer; only alphanumeric, -, and _ allowed', required=True)
        name_option = PulpCliOption('--display-name', 'user-readable display name for the consumer', required=False)
        description_option = PulpCliOption('--description', 'user-readable description for the consumer', required=False)
        d =  'adds/updates/deletes notes to programmtically identify the consumer; '
        d += 'key-value pairs must be separated by an equal sign (e.g. key=value); multiple notes can '
        d += 'be changed by specifying this option multiple times; notes are deleted by '
        d += 'specifying "" as the value'
        note_option = PulpCliOption('--note', d, required=False, allow_multiple=True)

        # Register Command
        register_command = PulpCliCommand('register', 'registers this consumer to the Pulp server', self.register)
        register_command.add_option(id_option)
        register_command.add_option(name_option)
        register_command.add_option(description_option)
        register_command.add_option(note_option)
        self.add_command(register_command)

        # Update Command
        update_command = PulpCliCommand('update', 'changes metadata of this consumer', self.update)
        update_command.add_option(name_option)
        update_command.add_option(description_option)
        update_command.add_option(note_option)
        self.add_command(update_command)

        # Unregister Command
        unregister_command = PulpCliCommand('unregister', 'unregisters this consumer from the Pulp server', self.unregister)
        d = 'if specified, the local consumer identification certificate will be ' \
        'removed even if the server cannot be contacted'
        unregister_command.create_flag('--force', _(d))
        self.add_command(unregister_command)

        # Bind Command
        bind_command = PulpCliCommand('bind', 'binds this consumer to a repository distributor for consuming published content', self.bind)
        bind_command.add_option(PulpCliOption('--repo-id', 'repository id', required=True))
        bind_command.add_option(PulpCliOption('--distributor-id', 'distributor id', required=True))
        self.add_command(bind_command)

        # Unbind Command
        unbind_command = PulpCliCommand('unbind', 'unbinds this consumer from a repository distributor', self.unbind)
        unbind_command.add_option(PulpCliOption('--repo-id', 'repository id', required=True))
        unbind_command.add_option(PulpCliOption('--distributor-id', 'distributor id', required=True))
        self.add_command(unbind_command)

        # History Retrieval Command
        history_command = PulpCliCommand('history', 'lists history of this consumer', self.history)
        d = 'limits displayed history entries to the given type;'
        d += 'supported types: ("consumer_registered", "consumer_unregistered", "repo_bound", "repo_unbound",'
        d += '"content_unit_installed", "content_unit_uninstalled", "unit_profile_changed", "added_to_group",'
        d += '"removed_from_group")'
        history_command.add_option(PulpCliOption('--event-type', d, required=False))
        history_command.add_option(PulpCliOption('--limit', 'limits displayed history entries to the given amount (must be greater than zero)', required=False))
        history_command.add_option(PulpCliOption('--sort', 'indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp', required=False))
        history_command.add_option(PulpCliOption('--start-date', 'only return entries that occur on or after the given date (format: yyyy-mm-dd)', required=False))
        history_command.add_option(PulpCliOption('--end-date', 'only return entries that occur on or before the given date (format: yyyy-mm-dd)', required=False))
        self.add_command(history_command)

    @property
    def consumerid(self):
        """
        Get the consumer ID from the consumer identity certificate.
        @return: The consumer id.  Returns (None) when not registered.
        @rtype: str
        """
        # Read path of consumer cert from config and check if consumer is already registered
        consumer_cert_path = self.context.config.get('filesystem', 'id_cert_dir')
        consumer_cert_filename = self.context.config.get('filesystem', 'id_cert_filename')
        full_filename = os.path.join(consumer_cert_path, consumer_cert_filename)
        bundle = Bundle(full_filename)
        if bundle.valid():
            content = bundle.read()
            x509 = X509.load_cert_string(content)
            subject = self.subject(x509)
            return subject['CN']
        else:
            return None


    def register(self, **kwargs):

        # Get consumer id
        id = kwargs['id']

        # Check if this consumer is already registered
        existing_consumer = self.consumerid
        if existing_consumer:
            m = 'This system has already been registered as a consumer. Please ' \
            'use the unregister command to remove the consumer before attempting ' \
            'to reregister.'
            self.prompt.render_failure_message(_(m))
            return

        # Get other consumer parameters
        name = id
        if 'display-name' in kwargs:
            name = kwargs['display-name']
        description = kwargs['description']
        notes = None
        if 'note' in kwargs.keys():
            if kwargs['note']:
                notes = self._parse_notes(kwargs['note'])

        # Check write permissions to cert directory
        id_cert_dir = self.context.config.get('filesystem', 'id_cert_dir')
        self.check_write_perms(id_cert_dir)

        # Set agent capabilities
        capabilities = dict(AgentCapabilities.default())

        # Call the server
        consumer = self.context.server.consumer.register(id, name, description, notes).response_body

        # Write consumer cert
        id_cert_name = self.context.config.get('filesystem', 'id_cert_filename')

        cert_filename = os.path.join(id_cert_dir, id_cert_name)

        f = open(cert_filename, 'w')
        f.write(consumer['certificate'])
        f.close()

        self.prompt.render_success_message('Consumer [%s] successfully registered' % id)

    def update(self, **kwargs):

        # Assemble the delta for all options that were passed in
        consumer_id = self.consumerid
        if not consumer_id:
            self.prompt.render_failure_message("This consumer is not registered to the Pulp server.")
            return
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        if 'note' in delta.keys():
            if delta['note']:
                delta['notes'] = self._parse_notes(delta['note'])
            delta.pop('note')
            
        try:
            self.context.server.consumer.update(consumer_id, delta)
            self.prompt.render_success_message('Consumer [%s] successfully updated' % consumer_id)
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % consumer_id, tag='not-found')

    def unregister(self, **kwargs):
        consumer_id = self.consumerid
        if not consumer_id:
            self.prompt.render_failure_message("This consumer is not registered to the Pulp server.")
            return

        def delete_cert():
            id_cert_dir = self.context.config.get('filesystem', 'id_cert_dir')
            id_cert_name = self.context.config.get('filesystem', 'id_cert_filename')
            cert_filename = os.path.join(id_cert_dir, id_cert_name)
            if os.path.exists(cert_filename):
                os.remove(cert_filename)


        try:
            self.context.server.consumer.unregister(consumer_id)
            delete_cert()
            self.prompt.render_success_message('Consumer [%s] successfully unregistered' % consumer_id)
        except Exception:
            if kwargs['force']:
                delete_cert()
                self.prompt.render_success_message('Consumer [%s] successfully unregistered' % consumer_id)
            else:
                raise

    def bind(self, **kwargs):
        consumer_id = self.consumerid
        if not consumer_id:
            self.prompt.render_failure_message("This consumer is not registered to the Pulp server.")
            return
        repo_id = kwargs['repo-id']
        distributor_id = kwargs['distributor-id']
        try:
            self.context.server.bind.bind(consumer_id, repo_id, distributor_id)
            self.prompt.render_success_message('Consumer [%s] successfully bound to repository distributor [%s : %s]' % (consumer_id, repo_id, distributor_id))
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % consumer_id, tag='not-found')

    def unbind(self, **kwargs):
        consumer_id = self.consumerid
        if not consumer_id:
            self.prompt.render_failure_message("This consumer is not registered to the Pulp server.")
            return
        repo_id = kwargs['repo-id']
        distributor_id = kwargs['distributor-id']
        try:
            self.context.server.bind.unbind(consumer_id, repo_id, distributor_id)
            self.prompt.render_success_message('Consumer [%s] successfully unbound from repository distributor [%s : %s]' % (consumer_id, repo_id, distributor_id))
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % consumer_id, tag='not-found')

    def history(self, **kwargs):
        consumer_id = self.consumerid
        if not consumer_id:
            self.prompt.render_failure_message("This consumer is not registered to the Pulp server.")
            return
        self.prompt.render_title(_('Consumer History [%(i)s]') % {'i' : consumer_id})

        history_list = self.context.server.consumer_history.history(consumer_id, kwargs['event-type'], kwargs['limit'], kwargs['sort'],
                                                            kwargs['start-date'], kwargs['end-date']).response_body
        filters = ['consumer_id', 'type', 'details', 'originator', 'timestamp']
        order = filters
        for history in history_list:
            self.prompt.render_document(history, filters=filters, order=order)

            
    def _parse_notes(self, notes_list):
        """
        Extracts notes information from the user-specified options and puts them in a dictionary
        @return: dict of notes
        @raises InvalidConfig: if one or more of the notes is malformed
        """
        notes_dict = {}
        for note in notes_list:
            pieces = note.split('=', 1)

            if len(pieces) < 2:
                raise InvalidConfig(_('Notes must be specified in the format key=value'))

            key = pieces[0]
            value = pieces[1]

            if value in (None, '', '""'):
                value = None

            if key in notes_dict.keys():
                self.prompt.write('Multiple values entered for a note with key [%s]. All except first value will be ignored.' % key)
                continue

            notes_dict[key] = value

        return notes_dict


    def subject(self, x509):
        """
        Get the certificate subject.
        note: Missing NID mapping for UID added to patch openssl.
        @return: A dictionary of subject fields.
        @rtype: dict
        """
        d = {}
        subject = x509.get_subject()
        subject.nid['UID'] = 458
        for key, nid in subject.nid.items():
            entry = subject.get_entries_by_nid(nid)
            if len(entry):
                asn1 = entry[0].get_data()
                d[key] = str(asn1)
                continue
        return d

    def check_write_perms(self, path):
        """
        Check that write permissions are present for the given path.  If parts
        of the path do not yet exist, check if it can be created.
        """
        if os.path.exists(path):
            if not os.access(path, os.W_OK):
                self.prompt.render_failure_message(_("Write permission is required for %s to perform this operation." %
                                    path))
            else:
                return True
        else:
            self.check_write_perms(os.path.split(path)[0])

