# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import importlib
import mock
import os
import unittest

from cloudbaseinit.plugins.windows import userdata_plugins
parthandler = importlib.import_module("cloudbaseinit.plugins.windows"
                                      ".userdata-plugins.parthandler")


class PartHandlerScriptHandlerTest(unittest.TestCase):

    def setUp(self):
        self.part_handler = parthandler.PartHandlerScriptHandler(
            userdata_plugins.PluginSet('fake_path'))

    def test_pathandler_process(self):
        fake_name = 'fake_name'
        os.makedirs = mock.MagicMock()

        part = mock.MagicMock()
        part.get_filename.return_value = fake_name
        subparts = mock.MagicMock()
        part.get_payload.return_value = subparts
        parthandler.load_from_file = mock.MagicMock()

        with mock.patch("cloudbaseinit.plugins.windows.userdata-plugins"
                        ".parthandler.open", mock.mock_open(), create=True):
            self.part_handler.process(part)

        os.makedirs.assert_called_with('fake_path' + "/part-handler/")
        part.get_filename.assert_called_with()
        part.get_payload.assert_called_with()
        self.assertTrue(parthandler.load_from_file.call_count == 2)
        self.assertTrue(self.part_handler.parent_set.has_custom_handlers)
