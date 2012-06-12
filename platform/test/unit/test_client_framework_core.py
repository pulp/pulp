#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

from pulp.client.extensions import core
from okaara.prompt import Recorder

# -- test cases ---------------------------------------------------------------

class RenderTests(unittest.TestCase):

    # These tests don't verify the visual output of the render functions; for
    # now while we're playing with what they look like it's just too much of a
    # pain. These tests at least call the methods to make sure they don't error
    # and verify the proper tags are specified.

    def test_render_title(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        p.render_title('Title')

        # Verify
        self.assertEqual(1, len(p.get_write_tags()))
        self.assertEqual(core.TAG_TITLE, p.get_write_tags()[0])

    def test_render_spacer(self):
        # Test
        r = Recorder()
        p = core.PulpPrompt(output=r, enable_color=False)
        p.render_spacer(lines=4)

        # Verify
        self.assertEqual(4, len(r.lines))
        self.assertEqual(0, len([l for l in r.lines if l != '\n']))

    def test_render_section(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        p.render_section('Section')

        # Verify
        self.assertEqual(1, len(p.get_write_tags()))
        self.assertEqual(core.TAG_SECTION, p.get_write_tags()[0])

    def test_render_paragraph(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        p.render_paragraph('Paragraph')

        # Verify
        self.assertEqual(1, len(p.get_write_tags()))
        self.assertEqual(core.TAG_PARAGRAPH, p.get_write_tags()[0])

    def test_render_success_message(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        p.render_success_message('Success')

        # Verify
        self.assertEqual(1, len(p.get_write_tags()))
        self.assertEqual(core.TAG_SUCCESS, p.get_write_tags()[0])

    def test_render_failure_message(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        p.render_failure_message('Failure', reason='Stuff broke')

        # Verify
        self.assertEqual(1, len(p.get_write_tags()))
        self.assertEqual(core.TAG_FAILURE, p.get_write_tags()[0])

    def test_render_document(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        doc = {'id' : 'd1', 'name' : 'document 1'}
        p.render_document(doc)

        # Verify
        self.assertEqual(len(doc), len(p.get_write_tags()))
        self.assertEqual(core.TAG_DOCUMENT, p.get_write_tags()[0])

    def test_render_document_list(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        docs = [
            {'id' : 'd1', 'name' : 'document 1'},
            {'id' : 'd2', 'name' : 'document 2'},
            {'id' : 'd3', 'name' : 'document 3'},
        ]
        p.render_document_list(docs)

        # Verify
        self.assertEqual(len(docs) * len(docs[0]), len(p.get_write_tags()))
        self.assertEqual(0, len([t for t in p.get_write_tags() if t is not core.TAG_DOCUMENT]))

    def test_render_document_list_with_filter(self):
        # Test
        r = Recorder()
        p = core.PulpPrompt(output=r, record_tags=True)
        docs = [
                {'id' : 'd1', 'name' : 'document 1'},
                {'id' : 'd2', 'name' : 'document 2'},
                {'id' : 'd3', 'name' : 'document 3'},
        ]
        p.render_document_list(docs, filters=['name'])

        # Verify
        self.assertEqual(len(docs), len(p.get_write_tags()))
        self.assertEqual(0, len([t for t in p.get_write_tags() if t is not core.TAG_DOCUMENT]))

        self.assertTrue('Name' in r.lines[1])
        self.assertEqual('\n', r.lines[2])
        self.assertTrue('Name' in r.lines[3]) # shouldn't be "Id" since that was filtered out

    def test_render_document_list_with_full_order(self):
        # Test
        r = Recorder()
        p = core.PulpPrompt(output=r, record_tags=True)
        docs = [
                {'id' : 'd1', 'name' : 'document 1'},
                {'id' : 'd2', 'name' : 'document 2'},
                {'id' : 'd3', 'name' : 'document 3'},
        ]
        p.render_document_list(docs, order=['name', 'id'])

        # Verify
        self.assertEqual(len(docs) * len(docs[0]), len(p.get_write_tags()))
        self.assertEqual(0, len([t for t in p.get_write_tags() if t is not core.TAG_DOCUMENT]))

        self.assertTrue('Name' in r.lines[1])
        self.assertTrue('Id' in r.lines[2])
        self.assertEqual('\n', r.lines[3])

    def test_render_document_list_with_partial_order(self):
        # Test
        r = Recorder()
        p = core.PulpPrompt(output=r, record_tags=True)
        docs = [
                {'id' : 'd1', 'name' : 'document 1', 'description' : 'description 1'},
        ]
        p.render_document_list(docs, order=['name'])

        # Verify
        self.assertEqual(len(docs)* len(docs[0]), len(p.get_write_tags()))
        self.assertEqual(0, len([t for t in p.get_write_tags() if t is not core.TAG_DOCUMENT]))

        self.assertTrue('Name' in r.lines[1])
        self.assertTrue('Description' in r.lines[2])
        self.assertTrue('Id' in r.lines[3])
        self.assertEqual('\n', r.lines[4])

    def test_render_document_list_order_and_filter(self):
        # Test
        r = Recorder()
        p = core.PulpPrompt(output=r, record_tags=True)
        docs = [
                {'id' : 'd1', 'name' : 'document 1', 'description' : 'description 1'},
        ]
        f = ['id', 'name']
        p.render_document_list(docs, order=['name'], filters=f)

        # Verify
        self.assertEqual(len(docs)* len(f), len(p.get_write_tags()))
        self.assertEqual(0, len([t for t in p.get_write_tags() if t is not core.TAG_DOCUMENT]))

        self.assertTrue('Name' in r.lines[1])
        self.assertTrue('Id' in r.lines[2])
        self.assertEqual('\n', r.lines[3])

    def test_render_document_list_no_items(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        docs = []
        p.render_document_list(docs)

        # Verify
        self.assertEqual(0, len(p.get_write_tags()))

    def test_create_progress_bar(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        pb = p.create_progress_bar()
        for i in range(0, 10):
            pb.render(i, 10)

        # Verify
        self.assertEqual(10, len(p.get_write_tags()))
        self.assertEqual(0, len([t for t in p.get_write_tags() if t is not core.TAG_PROGRESS_BAR]))

    def test_create_spinner(self):
        # Test
        p = core.PulpPrompt(record_tags=True)
        s = p.create_spinner()
        for i in range(0, 10):
            s.next()

        # Verify
        self.assertEqual(10, len(p.get_write_tags()))
        self.assertEqual(0, len([t for t in p.get_write_tags() if t is not core.TAG_SPINNER]))