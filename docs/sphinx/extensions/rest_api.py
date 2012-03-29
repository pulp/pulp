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

from docutils import nodes

# -- sphinx hook --------------------------------------------------------------

def setup(app):
    app.add_role('method', method_role)
    app.add_role('path', path_role)
    app.add_role('param_list', param_list_role)
    app.add_role('param', param_role)
    app.add_role('permission', permission_role)
    app.add_role('response_list', response_list_role)
    app.add_role('response_code', response_code_role)
    app.add_role('return', return_role)
    app.add_role('sample_request', sample_request_role)
    app.add_role('sample_response', sample_response_role)


# -- roles --------------------------------------------------------------------

def method_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Handles HTTP method. Examples: POST, GET, DELETE
    """

    n1 = _create_property_name_node('Method')
    n2 = nodes.inline(text=text.strip().upper())

    return [n1, n2], []

def path_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Handles the path to the API. Examples: /v2/repositories/<id>/units
    """

    n1 = _create_property_name_node('Path')
    n2 = nodes.literal(text='/pulp/api' + text.strip())

    return [n1, n2], []

def param_list_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Renders the header for the parameter nested list. Based on the type of
    method (passed in through text), different header text will be used to
    better describe where the values belong.

    Example data to pass to this role: POST, GET
    """

    # Look up the correct text
    headers = {
        ('post', 'put') : 'Request Body Contents',
        ('get', 'delete') : 'Query Parameters',
    }

    header = 'UNKNOWN METHOD TYPE'
    for k, v in headers.items():
        if text.lower() in k:
            header = v

    n1 = _create_property_name_node(header)
    return [n1], []

def param_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Handles the list of values accepted by the call. This is used to render
    both query parameters for GET calls and the valid body contents for POST calls.

    The text argument must contain three parts, separated by a comma:
    - parameter name
    - type
    - description

    If parameter name begins with ?, the description will be edited to indicate
    the parameter is optional.

    Example: id,str,uniquely identifies the repository
    """

    # Split apart the parameter name, type, and description
    param_parts = text.split(',', 2)
    param_name = param_parts[0].strip()
    param_type = param_parts[1].strip().lower()
    param_description = param_parts[2].strip()

    role_nodes = []

    # Handle name
    optional = param_name.startswith('?')
    if optional:
        param_name = param_name[1:]
    role_nodes.append(nodes.strong(text=param_name))

    # Handle type
    if param_type != '':
        # Safety net in case the python types are specified
        type_translations = {
            'str' : 'string',
            'int' : 'number',
            'dict' : 'object',
            'list' : 'array',
            'bool' : 'boolean',
        }
        param_type = type_translations.get(param_type, param_type)
        role_nodes.append(nodes.inline(text=' (%s) - ' % param_type))

    # Handle description
    if param_description != '':
        if optional:
            role_nodes.append(nodes.emphasis(text='(optional) '))
        param_description = _format_description(param_description)
        role_nodes.append(nodes.inline(text=param_description))

    return role_nodes, []

def permission_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Handles the permissions required for the call. Examples: create, delete, update
    """

    n1 = _create_property_name_node('Permission')
    n2 = nodes.inline(text=text.strip().lower())

    return [n1, n2], []

def response_list_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Renders the title of the responses section to be displayed above the
    nested list of responses.

    Due to how sphinx works, a non-whitespace value must be specified when
    calling the role. It's value is ignored.

    Example usage:  :response_list:`_`
    """

    n1 = _create_property_name_node('Response Codes')
    return [n1], []

def response_code_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Handles a single HTTP response code and description. They are specified
    together in the value for the role and separated by a comma. The description,
    however, is optional.

    Example: 409,if a repository with the given ID already exists
    """

    parts = text.split(',', 1)

    code = parts[0].strip()
    n1 = nodes.strong(text=code)

    created_nodes = [n1]

    if len(parts) > 1:
        description = ' '.join(parts[1:]).strip()
        description = _format_description(description)
        n2 = nodes.inline(text=' - ' + description)
        created_nodes.append(n2)

    return created_nodes, []

def return_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Handles the description of what is returned from the call.
    """

    n1 = _create_property_name_node('Return')
    description = _format_description(text.strip())
    n2 = nodes.inline(text=description)

    return [n1, n2], []

def sample_request_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Renders the header before a sample request body. The body itself is not
    included to this role and should be properly indented to be rendered as a
    code section.

    Due to how sphinx works, a non-whitespace value must be specified when
    calling the role. It's value is ignored. Also due to how sphinx works, the
    :: after invoking this role to do start a code block must have a space
    after the role invocation.

    Example usage: :sample_request:`_` ::
    """

    n1 = _create_property_name_node('Sample Request')
    return [n1], []

def sample_response_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Renders the header before a sample response body. The response code being
    sampled is specified in the text parameter.

    Due to how sphinx works, the :: after invoking this role to do start a code
    block must have a space after the role invocation.

    Example usage: :sample_response:`200` ::
    """

    n1 = _create_property_name_node('Sample %s Response Body' % text)
    return [n1], []

def _create_property_name_node(name):
    """
    Creates the node to be used as the name of the property being displayed
    (e.g. "method", "permission", "responses". The specified name should be
    devoid of punctuation and spaces.

    This is simply meant as a utility to ensure consistent formatting.

    @param name: property name to display
    @return: node that should be returned at the start of the role's returned
             list of nodes
    """
    formatted = '%s: ' % name
    property_node = nodes.strong(text=formatted)
    return property_node

def _format_description(description):
    """
    Correctly capitalizes text in a description.

    @return: formatted description
    """
    if len(description) is 0:
        return description
    else:
        return description[0].lower() + description[1:]