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

from gettext import gettext as _

from pulp.gc_client.framework.extensions import PulpCliCommand

# -- constants ----------------------------------------------------------------

TYPE_RPM = 'rpm'
TYPE_ERRATA = 'errata'

LOG = None # set by context

# -- plugin hook --------------------------------------------------------------

def initialize(context):

    global LOG
    LOG = context.logger

    repo_section = context.cli.find_section('repo')
    copy_section = repo_section.create_subsection('copy', _('copy packages and errata between repositories'))

    rpm_usage_desc = 'Packages to copy from the source repository are determined by ' \
    'applying regular expressions for inclusion (match) and exclusion (not). ' \
    'Criteria are specified in the format "field=regex", for example "name=python.*". ' \
    'Valid fields are: name, epoch, version, release, arch, buildhost, checksum, ' \
    'description, filename, license, and vendor.'
    copy_section.add_command(CopyCommand(context, 'rpms', _('copies RPMs from one repository into another'), _(rpm_usage_desc), TYPE_RPM))

# -- commands -----------------------------------------------------------------

class CopyCommand(PulpCliCommand):

    def __init__(self, context, name, description, usage_description, type_id):
        self.context = context
        self.type_id = type_id

        PulpCliCommand.__init__(self, name, description, self.copy, usage_description=usage_description)

        # General Options
        self.create_option('--from-repo-id', _('source repository from which units will be copied'), ['-f'], required=True)
        self.create_option('--to-repo-id', _('destination repository to copy units into'), ['-t'], required=True)
        self.create_flag('--dry-run', _('display the units that will be copied without performing the actual copy'), ['-d'])

        # Criteria Options
        general = 'specified in the format "field=value"; '\
                  'the value may be either a literal value or a regular expression; '\
                  'multiple match expressions may be passed in by specifying the '\
                  'flag multiple times'
        general = _(general)

        m = 'field and expression to match when determining units for inclusion, '
        m = _(m) + general

        self.create_option('--match', m, ['-m'], required=False, allow_multiple=True)

        n = 'field and expression to omit when determining units for includion, '
        n = _(n) + general

        self.create_option('--not', n, ['-n'], required=False, allow_multiple=True)


    def copy(self, **kwargs):
        from_repo = kwargs['from-repo-id']
        to_repo = kwargs['to-repo-id']

        criteria = args_to_criteria(self.type_id, kwargs)

        if 'dry-run' in kwargs and kwargs['dry-run']:
            matching_units = self.context.server.repo_search.search(from_repo, criteria).response_body
            matching_units_metadata = [u['metadata'] for u in matching_units]

            self.context.prompt.render_title(_('Matching Units'))
            self.context.prompt.render_document_list(matching_units_metadata, filters=['filename'], num_separator_spaces=0)
        else:
            self.context.server.repo_unit_associations.copy_units(from_repo, to_repo, criteria)
            self.context.prompt.render_success_message(_('Successfully copied matching units'))
# -- utility ------------------------------------------------------------------

class InvalidCriteria(Exception):
    """
    Exception raised when the user specifies criteria options that cannot be
    converted into the necessary Pulp syntax. The argument passed in (e[0]) is
    the message that should be i18n'd and displayed to the user.
    """
    pass

def args_to_criteria(type_id, kwargs):
    """
    Translates relevant user entered arguments into the proper format to be
    submitted to the server as the unit copy criteria.

    @param kwargs: map of user entered options and values; may contain extra
                   options that this call does not care about
    @dict  kwargs: dict

    @return: value to be passed to the criteria argument on the unit copy call
    @rtype:  dict
    """

    # Simple part  :)
    criteria = {'type_ids' : [type_id]}

    match_clauses = []
    not_clauses = []

    # Convert all "match" pairs into mongo syntax
    if 'match' in kwargs and kwargs['match'] is not None:
        match_clauses = _parse(kwargs['match'], lambda x, y: {x : {'$regex' : y}})

    # Convert all "not" pairs into mongo syntax
    if 'not' in kwargs and kwargs['not'] is not None:
        not_clauses = _parse(kwargs['not'], lambda x, y: {x : {'$not' : y}})

    # Concatenate all of them into an $and clause
    all_clauses = match_clauses + not_clauses
    if len(all_clauses) > 0:
        if len(all_clauses) > 1:
            unit_filters_clause = {'$and' : all_clauses}
        else:
            unit_filters_clause = all_clauses[0]
        criteria['filters'] = {'unit' : unit_filters_clause}

    return criteria

def _parse(args, mongo_func):
    """
    Parses a list of user supplied key value pairs and creates the appropriate
    mongo syntax based on the type of relationship being defined.

    The provided function must accept two parameters, the field name and value,
    and return the corresponding mongo clause that should be added to the
    criteria.

    If any of the arguments cannot correctly be parsed an exception is raised
    describing the issue.

    @param args: list of unparsed key/value pairs, expressed as "field=value"
    @type  args: list

    @param mongo_func: function to apply to the value
    @type  mongo_func: func

    @return: list of mongo syntax clauses to add to the criteria
    """

    # Consolidate multiple match calls with the same field into a single list
    clauses = []
    for user_opt in args:
        field, value = _split(user_opt)
        clause = mongo_func(field, value)
        clauses.append(clause)

    return clauses

def _split(opt):
    """
    Splits the user given option into a field/value tuple and returns it,
    raising an exception if the option is malformed.

    @param opt: value the user passed in as a criteria option; expected to
                be in the format key=value
    @return: tuple of key and value
    """
    pieces = opt.split('=')
    if len(pieces) != 2:
        raise InvalidCriteria('Criteria values must be specified in the format "field=value"')
    return pieces[0], pieces[1]


