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

from cloudbaseinit.metadata.services import base as metadata_services_base
from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import userdata
from cloudbaseinit.osutils import base as osutils_base


class UserDataTest(unittest.TestCase):
    '''testing the userdata module'''

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()
        self.service = metadata_services_base.BaseMetadataService()
        self.obj = userdata.UserDataPlugin()
        self.fake_user_data = 'rem cmd '
        self.execute_process = osutils_base.BaseOSUtils.execute_process

    def _setup_stubs(self):
        self.mox.StubOutWithMock(metadata_services_base.BaseMetadataService,
                                 'get_user_data')
        self.mox.StubOutWithMock(osutils_base.BaseOSUtils, 'execute_process')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_no_user_data(self):
        m = self.service.get_user_data('openstack')
        m.AndReturn(False)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)

        self.mox.VerifyAll()
        self.assertEqual(
            response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_no_user_data(self):
        m = self.service.get_user_data('openstack')
        m.AndReturn(None)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_invalid_user_data(self):
        self.fake_user_data = 'fake data'
        m = self.service.get_user_data('openstack')
        m.AndReturn(self.fake_user_data)
        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_user_data_execution_exception(self):
        m = self.service.get_user_data('openstack')
        m.AndReturn(self.fake_user_data)

        m = self.execute_process(mox.IsA(list), True)
        m.AndRaise(BaseException)
        self.mox.ReplayAll()
        self.assertRaises(BaseException, self.obj.execute, self.service)
        self.mox.VerifyAll()

    def test_ps1_execution(self):
        self.fake_user_data = '#ps1 '
        m = self.service.get_user_data('openstack')
        m.AndReturn(self.fake_user_data)
        m = self.execute_process(['powershell.exe'], False)
        m.AndReturn((None, None, 0))
        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_cmd_execution(self):
        self.fake_user_data = 'rem cmd '
        m = self.service.get_user_data('openstack')
        m.AndReturn(self.fake_user_data)
        m = self.execute_process([mox.IsA(str)], True)
        m.AndReturn((None, None, 0))
        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_sh_execution(self):
        self.fake_user_data = '#! '
        m = self.service.get_user_data('openstack')
        m.AndReturn(self.fake_user_data)
        m = osutils_base.BaseOSUtils.execute_process(['bash.exe'], True)
        m.AndReturn((None, None, 0))
        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))
