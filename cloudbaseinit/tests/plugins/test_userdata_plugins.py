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

import glob
import imp
import mox
import unittest

from cloudbaseinit.plugins.windows import userdata_plugins


class PluginSetTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.fake_path = 'fake/path'
        self.files = ['fake/path/file1.py',
                      'fake/path/file2.py']
        self.obj = userdata_plugins.PluginSet(self.fake_path)

    def _setup_stubs(self):
        self.mox.StubOutWithMock(glob, 'glob')
        self.mox.StubOutWithMock(imp, 'load_source')
        self.mox.StubOutWithMock(imp, 'load_compiled')

    def tearDown(self):
        self.mox.UnsetStubs()

    def _test_load(self, files, sets):
        m = glob.glob(self.fake_path + '/*.py')
        m.AndReturn(files)

        mock = self.mox.CreateMockAnything()
        for f in files:
            m = imp.load_source(f, self.fake_path)
            self.obj.set[mock.type] = mock
            m.AndReturn(sets)

        self.mox.ReplayAll()
        self.obj.load()
        self.mox.VerifyAll()
        self.assertIsNotNone(self.obj.set)

    def test_load(self):
        self._test_load(self.files, self.obj.set)

    def test_load_no_files(self):
        files = []
        self._test_load(files, self.obj.set)

    def test_no_plugin(self):
        self._test_load(self.files, None)
