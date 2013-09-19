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

import imp
import importlib
import io
import mox
import os
import unittest

from cloudbaseinit.osutils import factory
from cloudbaseinit.osutils import windows as winutils
from cloudbaseinit.plugins.windows import userdata_plugins
parthandler = importlib.import_module("cloudbaseinit.plugins.windows"
                                      ".userdata-plugins.parthandler")


class PartHandlerScriptHandlerTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.path = 'fake_name'
        self.fake_name = 'fake_name'
        self.parent_set = userdata_plugins.PluginSet(self.path)
        self.fake_part = self.mox.CreateMockAnything()
        self.obj = parthandler.PartHandlerScriptHandler(self.parent_set)
        self.subparts = ['Content-Type: text/x-cfninitdata; '
                         'charset="us-ascii"',
                         'MIME-Version: 1.0',
                         'Content-Transfer-Encoding: 7bit',
                         'Content-Disposition: attachment;',
                         'filename="cfn-userdata"']

    def _setup_stubs(self):
        self.mox.StubOutWithMock(factory.OSUtilsFactory, 'get_os_utils')
        self.mox.StubOutWithMock(winutils.WindowsUtils, 'open_file')
        self.mox.StubOutWithMock(os, 'makedirs')
        self.mox.StubOutWithMock(imp, 'load_compiled')
        self.mox.StubOutWithMock(imp, 'load_source')
        self.mox.StubOutWithMock(importlib, 'import_module')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_parthandles(self):
        os.makedirs('fake_name/part-handler/')
        m = factory.OSUtilsFactory.get_os_utils()
        os_utils = winutils.WindowsUtils()
        m.AndReturn(os_utils)

        m = self.fake_part.get_filename()
        m.AndReturn('fake_name.py')

        m = self.fake_part.get_payload()
        m.AndReturn(self.subparts)

        m = os_utils.open_file(mox.IsA(str), 'wb')
        handle = self.mox.CreateMockAnything()
        m.AndReturn(handle)

        handle.__enter__().AndReturn(handle)
        handle.write(self.subparts)
        handle.__exit__(None, None, None).AndReturn(None)

        list_types = self.mox.CreateMockAnything()
        m = imp.load_source(mox.IsA(str), mox.IsA(str))
        m.AndReturn(list_types)

        m = importlib.import_module(mox.IsA(str))
        m.AndReturn(list_types)

        m = imp.load_source(mox.IsA(str), mox.IsA(str))
        m.AndReturn(self.fake_part)
        m = importlib.import_module(mox.IsA(str))
        m.AndReturn(self.fake_part)

        m = list_types.list_types()
        m.AndReturn(self.subparts)

        self.mox.ReplayAll()
        response = self.obj.process(self.fake_part)
        self.mox.VerifyAll()
        self.assertIsNone(response)

        self.assertTrue(self.parent_set.has_custom_handlers)
        self.assertIsNotNone(self.parent_set.custom_handlers)
