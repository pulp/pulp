from pulp.client.extensions.extensions import PulpCliSection


def initialize(context):

    section = PulpCliSection('section-3', 'Section 3')
    context.cli.add_section(section)
