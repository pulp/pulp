from pulp.client.extensions.extensions import PulpCliSection


def initialize(context):
    section = PulpCliSection('section-not-python-module', 'Section Busted')
    context.cli.add_section(section)
