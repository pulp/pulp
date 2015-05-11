from pulp.client.extensions.extensions import PulpCliSection


def initialize(context):

    section = PulpCliSection('section-1', 'Section 1')
    context.cli.add_section(section)
