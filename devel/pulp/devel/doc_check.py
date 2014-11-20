from itertools import chain
import ast, _ast
import os
import sys


ERR_NO_PARAM_TEMPLATE = "Function %s is missing sphinx param definition for argument %s (%s:%i)"
ERR_NO_TYPE_TEMPLATE = "Function %s is missing sphinx type definition for argument %s (%s:%i)"
ERR_NO_RTYPE_TEMPLATE = "Function %s is missing sphinx type definition for return type (%s:%i)"
ERR_NO_RETURNS_TEMPLATE = "Function %s is missing sphinx definition for return statement (%s:%i)"


def recursive_check(path):
    """
    Walk the directory tree at the given path and search for docstrings that are missing param and
    type definitions.

    :param path: The path that should be checked
    :type  path: basestring
    """
    checker = RunDocstringCheck()
    errors = []
    for root, dirs, files in os.walk(path):
        # skip build and test dirs
        if 'test' in root or 'build' in root:
            continue
        for f in files:
            if f.endswith(".py"):
                checker.check(os.path.join(root, f))
                errors.append(checker.get_errors())

    errlist = list(chain.from_iterable(errors))
    if errlist:
        for error in errlist:
            print error
        print "found undocumented parameters!"
        sys.exit(1)


class FindDocstrings(ast.NodeVisitor):
    """
    AST visitor to find functions with incomplete docstrings.

    Currently checks to see that all parameters are mentioned in docstring.
    """

    def __init__(self, src_filename):
        """
        Initialize doc checker

        :param src_filename: filename of source to check
        :type  src_filename: str
        """

        self.src_filename = src_filename
        self.error_list = []

    def generic_visit(self, node):
        """
        visits any non-function AST node

        :param node: AST node to visit
        :type  node: compiler.ast.Node
        """

        ast.NodeVisitor.generic_visit(self, node)

    def visit_FunctionDef(self, node):
        """
        visits FunctionDef AST nodes and does docstring checks

        :param node: AST node to visit
        :type  node: compiler.ast.Node
        """

        PARAM_STR = ":param %s:"
        TYPE_STR_TWOSPACE = ":type  %s:"
        RTYPE = ":rtype:"
        RETURNS = ":return:"

        docstring = ast.get_docstring(node)
        if node.args:
            arglist = node.args.args
            for param in arglist:
                if param.id == 'self' or param.id == 'cls':
                    continue
                # if there is no docstring, just keep going. It will get caught
                # by pep257 checks
                if docstring and 'See super' not in docstring:
                    if PARAM_STR % param.id not in docstring:
                        self.error_list.append(ERR_NO_PARAM_TEMPLATE %
                                               (node.name, param.id,
                                                self.src_filename, param.lineno))
                    if TYPE_STR_TWOSPACE % param.id not in docstring:
                        self.error_list.append(ERR_NO_TYPE_TEMPLATE %
                                               (node.name, param.id,
                                                self.src_filename, param.lineno))
        for statement in node.body:
            # if there's a return statement, check for additional docs
            if isinstance(statement, _ast.Return) and \
               docstring and 'See super' not in docstring:
                if RTYPE not in docstring:
                    self.error_list.append(ERR_NO_RTYPE_TEMPLATE %
                                           (node.name, self.src_filename, statement.lineno))
                if RETURNS not in docstring:
                    self.error_list.append(ERR_NO_RETURNS_TEMPLATE %
                                           (node.name, self.src_filename, statement.lineno))

        ast.NodeVisitor.generic_visit(self, node)


class RunDocstringCheck():
    """
    Wrapper for FindDocstrings.
    """

    def check(self, src_filename):
        """
        checks docstrings for a file

        :param src_filename: source filename to check
        :type  src_filename: str
        """
        self.finder = FindDocstrings(src_filename)
        with open(src_filename) as src_fd:
            src_str = file.read(src_fd)
            root_node = ast.parse(src_str, filename=src_filename)
            self.finder.visit(root_node)

    def get_errors(self):
        """
        return found errors
        :return: list of errors
        :rtype: list
        """
        return self.finder.error_list
