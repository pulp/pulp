"""
Contains knowledge about notifiers in the server as well as the ability to
retrieve the appropriate method needed to handle an event.

Currently this implementation assumes a hardcoded set of notifiers in the server.
Eventually this will likely change to dynamically load notifiers (yet another
plugin point for Pulp) but for current (Jun 21, 2012) needs this is fine.
"""

from pulp.server.event import amqp, http, mail


# Set in the reset() method
NOTIFIER_FUNCTIONS = None


def is_valid_notifier_type_id(type_id):
    """
    @param type_id: type ID to check
    @type  type_id: str

    @return: true if there is a notifier with the given type; false otherwise
    @rtype:  bool
    """
    return type_id in NOTIFIER_FUNCTIONS


def get_notifier_function(type_id):
    """
    Returns the appropriate function to invoke to handle an event. The
    signature of the function will accept the following arguments:

    - The event being fired (an Event object from the data module)
    - The configuration to use for the notifier (a JSON document), specified
      when the user wired up this notifier to a particular event type

    @param type_id: type of notifier to retrieve
    @type  type_id: str

    @return: function to invoke to perform the notifier's functionality
    @rtype:  callable
    """
    return NOTIFIER_FUNCTIONS[type_id]


def reset():
    """
    Initializes the mappings between notifier ID and method to invoke. This
    will automatically be called when the module is first loaded and should
    only need to be called again in unit test cleanup.
    """
    global NOTIFIER_FUNCTIONS
    NOTIFIER_FUNCTIONS = {
        http.TYPE_ID: http.handle_event,
        mail.TYPE_ID: mail.handle_event,
        amqp.TYPE_ID: amqp.handle_event,
    }

# Perform the initial populating of the notifier functions on module load
reset()
