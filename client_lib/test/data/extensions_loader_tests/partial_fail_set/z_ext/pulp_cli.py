from pulp.client.extensions.extensions import PulpCliSection


def initialize(context):
    section = PulpCliSection('section-z', 'Section Z')
    context.cli.add_section(section)
