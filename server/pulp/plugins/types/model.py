"""
Non-database domain objects used to describe content types.
"""


class TypeDescriptor:
    """
    Carries information on a single type descriptor.
    """

    def __init__(self, filename, contents):
        """
        @param filename: name of the file from which the contents were
                         extracted (used for identification purposes in
                         logging and errors)
        @type  filename: str

        @param contents: contents read from the descriptor
        @type  contents: str
        """
        self.filename = filename
        self.contents = contents
        self.parsed = None  # stores the parsed version of the contents


class TypeDefinition:
    """
    Once a type descriptor has been parsed, instances of this class will
    describe the types to be loaded.
    """

    def __init__(self, id, display_name, description, unit_key, search_indexes, referenced_types):
        self.id = id
        self.display_name = display_name
        self.description = description

        if not isinstance(unit_key, (list, tuple)):
            unit_key = [unit_key]

        if not isinstance(search_indexes, (list, tuple)):
            search_indexes = [search_indexes]

        if not isinstance(referenced_types, (list, tuple)):
            referenced_types = [referenced_types]

        self.unit_key = unit_key
        self.search_indexes = search_indexes
        self.referenced_types = referenced_types
