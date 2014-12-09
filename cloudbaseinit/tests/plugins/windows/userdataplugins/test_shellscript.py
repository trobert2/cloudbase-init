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

import mock
import os
import unittest

from cloudbaseinit.plugins.windows.userdataplugins import shellscript


class ShellScriptPluginTests(unittest.TestCase):

    def setUp(self):
        self._shellscript = shellscript.ShellScriptPlugin()

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('tempfile.gettempdir')
    @mock.patch('cloudbaseinit.plugins.windows.fileexecutils.exec_file')
    @mock.patch('cloudbaseinit.utils.encoding.write_file')
    def _test_process(self, mock_write_file, mock_exec_file, mock_gettempdir,
                      mock_get_os_utils, exception=False):
        fake_dir_path = os.path.join("fake", "dir")
        mock_osutils = mock.MagicMock()
        mock_part = mock.MagicMock()
        mock_part.get_filename.return_value = "fake_filename"
        mock_gettempdir.return_value = fake_dir_path
        mock_get_os_utils.return_value = mock_osutils
        fake_target = os.path.join(fake_dir_path, "fake_filename")
        mock_exec_file.return_value = 'fake response'

        if exception:
            mock_exec_file.side_effect = [Exception]
        with mock.patch("cloudbaseinit.plugins.windows.userdataplugins."
                        "shellscript.open", mock.mock_open(), create=True):
            response = self._shellscript.process(mock_part)

        mock_part.get_filename.assert_called_once_with()
        mock_write_file.assert_called_once_with(
            fake_target, mock_part.get_payload.return_value)
        mock_exec_file.assert_called_once_with(fake_target)
        mock_part.get_payload.assert_called_once_with()
        mock_gettempdir.assert_called_once_with()
        if not exception:
            self.assertEqual('fake response', response)

    def test_process(self):
        self._test_process(exception=False)

    def test_process_exception(self):
        self._test_process(exception=True)
