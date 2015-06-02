"""
Mock cursor object used to aid in testing methods that reutn pymongo cursors
"""


class MockCursor():
    def __init__(self, contents):
        self.contents = contents
        self.num = 0

    def __iter__(self):
        return self

    def count(self):
        return len(self.contents)

    def next(self):
        if self.num < len(self.contents):
            current = self.contents[self.num]
            self.num += 1
            return current
        else:
            raise StopIteration()
