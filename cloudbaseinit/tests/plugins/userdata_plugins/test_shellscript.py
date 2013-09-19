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

import mox
import os
import unittest
import importlib

from cloudbaseinit.osutils import factory
from cloudbaseinit.osutils import windows as winutils
shellscript = importlib.import_module("cloudbaseinit.plugins.windows"
                                      ".userdata-plugins.shellscript")


class ShellScriptHandlerTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.fake_part = self.mox.CreateMockAnything()
        self.parent_set = 'fake'
        self.path = 'fake/fake'
        self.obj = shellscript.ShellScriptHandler(self.parent_set)
        self.subparts = ['Content-Type: text/x-cfninitdata; '
                         'charset="us-ascii"',
                         'MIME-Version: 1.0',
                         'Content-Transfer-Encoding: 7bit',
                         'Content-Disposition: attachment;',
                         'filename="cfn-userdata"']

    def _setup_stubs(self):
        self.mox.StubOutWithMock(factory.OSUtilsFactory, 'get_os_utils')
        self.mox.StubOutWithMock(os, 'remove')
        self.mox.StubOutWithMock(winutils.WindowsUtils, 'open_file')
        self.mox.StubOutWithMock(winutils.WindowsUtils, 'execute_process')

    def tearDown(self):
        self.mox.UnsetStubs()

    def _test_shellscript(self, filename, args, shell=False):
        m = factory.OSUtilsFactory.get_os_utils()
        os_utils = winutils.WindowsUtils()
        m.AndReturn(os_utils)

        m = self.fake_part.get_filename()
        m.AndReturn(filename)

        if filename.endswith((".cmd", ".sh", ".ps1")):
            m = os_utils.open_file(mox.IsA(str), 'wb')
            handle = self.mox.CreateMockAnything()
            m.AndReturn(handle)
            handle.__enter__().AndReturn(handle)
            m = self.fake_part.get_payload()
            m.AndReturn(self.subparts)
            handle.write(self.subparts)
            handle.__exit__(None, None, None).AndReturn(None)

            winutils.WindowsUtils.execute_process(args, shell)

        self.mox.ReplayAll()
        response = self.obj.process(self.fake_part)
        self.mox.VerifyAll()
        self.assertFalse(response)

    def test_batch_script(self):
        self._test_shellscript('fake.cmd', self.path, True)

    def test_shell_script(self):
        self._test_shellscript('fake.sh', ['bash.exe', self.path], False)

    def test_powershell_script(self):
        self._test_shellscript('fake.ps1', ['powershell.exe',
                                            '-ExecutionPolicy', 'RemoteSigned',
                                            '-NonInteractive', self.path],
                               False)

    def test_unsuported_format(self):
        self._test_shellscript('fake.txt', self.path)

    def test_exception_error(self):
        m = factory.OSUtilsFactory.get_os_utils()
        os_utils = winutils.WindowsUtils()
        m.AndReturn(os_utils)

        m = self.fake_part.get_filename()
        m.AndReturn(None)

        self.mox.ReplayAll()
        self.assertRaises(Exception, self.obj.process, self.fake_part)
        self.mox.VerifyAll()
