import sys
sys.path.insert(0, '../../')

import unittest
from pulp.perspectives import PerspectiveManager

class TestPerspectives(unittest.TestCase):
    
    def test_get_all_perspectives(self):
        pm = PerspectiveManager()
        all = pm.get_all_perspectives()
        assert (all is not None)
        root = all['root']
        assert (root is not None)
        assert (root.name == 'root')
        assert (root.url == '/')
        content = all['content']
        assert (content is not None)
        assert (content.tasks is not None)
        t = content.tasks[0]
        assert (t.url is not None)
        assert (t.urlmatches is not None)
        umatch = t.urlmatches[0]
        assert umatch is not None
        
        