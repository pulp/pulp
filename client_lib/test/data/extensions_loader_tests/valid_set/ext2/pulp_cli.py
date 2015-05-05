from pulp.client.extensions.extensions import PulpCliSection


def initialize(context):
    section = PulpCliSection('section-2', 'Section 2')
    context.cli.add_section(section)
