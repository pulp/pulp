import os


class AliasTable(object):
    """
    Represents a collection of Apache *Alias* directives.

    :ivar table: A table of alias => path mappings.
    :type table: dict
    """

    def __init__(self):
        self.table = {}

    def load(self):
        """
        Load the alias table.
        Read .conf files in /etc/httpd/conf.d/ and build the table
        using *Alias* directives.
        """
        root = '/etc/httpd/conf.d'
        for path in [os.path.join(root, f) for f in os.listdir(root)]:
            if not path.endswith('.conf'):
                continue
            with open(path) as fp:
                while True:
                    line = fp.readline()
                    if not line:
                        break
                    if not line.startswith('Alias'):
                        # Not an Alias
                        continue
                    parts = line.split(' ')
                    if len(parts) != 3:
                        # Malformed
                        continue
                    self.table[parts[1].strip()] = parts[2].strip()

    def translate(self, path):
        """
        Translate the specified *path* component of a URL by
        replacing the matched alias with the path mapped to the alias.
        The original *path* is returned when it cannot be translated.

        :param path: The *path* component of a URL.
        :type path: str
        :return: A translated path.
        :rtype: str
        """
        translated = path
        for alias, real in sorted(self.table.items()):
            if path.startswith(alias):
                translated = path.replace(alias, real)
                break
        return os.path.realpath(translated)
