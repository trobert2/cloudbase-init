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
import tempfile
import unittest

from cloudbaseinit.osutils import factory
from cloudbaseinit.plugins.windows import userdata_plugins
shellscript = importlib.import_module("cloudbaseinit.plugins.windows"
                                      ".userdata-plugins.shellscript")


class ShellScriptHandlerTest(unittest.TestCase):

    def setUp(self):
        self.shell_script = shellscript.ShellScriptHandler(
            userdata_plugins.PluginSet('fake_path'))

    def _test_shellscript_process(self, filename, args, shell=False):
        part = mock.MagicMock()
        part.get_filename.return_value = filename
        tempfile.gettempdir = mock.MagicMock(return_value='directory')
        osutils = mock.MagicMock()

        factory.OSUtilsFactory.get_os_utils = mock.MagicMock(
            return_value=osutils)

        subparts = mock.MagicMock()
        part.get_payload.return_value = subparts

        with mock.patch("cloudbaseinit.plugins.windows.userdata-plugins"
                        ".shellscript.open", mock.mock_open(), create=True):
            response = self.shell_script.process(part)

        if filename.endswith((".cmd", ".sh", ".ps1")):
            part.get_filename.assert_called_with()
            part.get_payload.assert_called_with()
            osutils.execute_process.assert_called_with(args, shell)
        self.assertFalse(response)

    def test_batch_script(self):
        self._test_shellscript_process('fake.cmd',
                                       ['directory\\fake.cmd'], True)

    def test_shell_script(self):
        self._test_shellscript_process('fake.sh', ['bash.exe',
                                                   'directory\\fake.sh'],
                                       False)

    def test_powershell_script(self):
        self._test_shellscript_process('fake.ps1', ['powershell.exe',
                                                    '-ExecutionPolicy',
                                                    'RemoteSigned',
                                                    '-NonInteractive',
                                                    'directory\\fake.ps1'],
                                       False)

    def test_unsuported_format(self):
        self._test_shellscript_process('fake.txt', 'fake_path')

    def test_exception_error(self):
        part = mock.MagicMock()
        self.assertRaises(Exception, self.shell_script.process, part)
