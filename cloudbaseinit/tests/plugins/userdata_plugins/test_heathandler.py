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
import unittest
import importlib

from cloudbaseinit.plugins.windows import userdata
heathandler = importlib.import_module("cloudbaseinit.plugins.windows"
                                      ".userdata-plugins.heathandler")


class HeatUserDataHandlerTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.fake_part = self.mox.CreateMockAnything()
        self.parent_set = 'fake'
        self.obj = heathandler.HeatUserDataHandler(self.parent_set)
        self.fake_filename = "cfn-userdata"
        self.subparts = ['Content-Type: text/x-cfninitdata; '
                         'charset="us-ascii"',
                         'MIME-Version: 1.0',
                         'Content-Transfer-Encoding: 7bit',
                         'Content-Disposition: attachment;',
                         'filename="cfn-userdata"']

    def _setup_stubs(self):
        self.mox.StubOutWithMock(userdata, 'handle')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_heathandler(self):

        m = self.fake_part.get_filename()
        m.AndReturn(self.fake_filename)

        m = self.fake_part.get_payload()
        m.AndReturn(self.subparts)

        m = userdata.handle(self.subparts)
        m.AndReturn((1, False))

        self.mox.ReplayAll()
        response = self.obj.process(self.fake_part)
        self.mox.VerifyAll()
        self.assertIsNone(response)
