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

from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.metadata.services import httpservice
from cloudbaseinit.osutils import factory
from cloudbaseinit.osutils import windows
from cloudbaseinit.plugins import base as base_plugin
from cloudbaseinit.plugins.windows import createuser
from cloudbaseinit.tests.metadata import json_data

CONF = cfg.CONF


class CreateUserPluginTest(unittest.TestCase):
    ''' testing user creation plugin '''

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.svc = createuser.CreateUserPlugin()
        self.json_metadata = json_data.get_fake_metadata_json('2013-04-04')
        self.username = 'Admin'
        self.group = 'Group'
        self.osutils = windows.WindowsUtils()
        self.service = httpservice.HttpService
        self.execution_done = base_plugin.PLUGIN_EXECUTION_DONE

    def _setup_stubs(self):
        self.mox.StubOutWithMock(windows.WindowsUtils, 'create_user')
        self.mox.StubOutWithMock(httpservice.HttpService, 'get_meta_data')
        self.mox.StubOutWithMock(factory.OSUtilsFactory, 'get_os_utils')
        self.mox.StubOutWithMock(windows.WindowsUtils,
                                 'create_user_logon_session')
        self.mox.StubOutWithMock(windows.WindowsUtils,
                                 'close_user_logon_session')
        self.mox.StubOutWithMock(windows.WindowsUtils,
                                 'add_user_to_local_group')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'user_exists')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'set_user_password')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_create_user(self):
        m = factory.OSUtilsFactory.get_os_utils()
        m.AndReturn(self.osutils)

        m = httpservice.HttpService.get_meta_data(mox.IsA(str))
        m.AndReturn(self.json_metadata)

        m = self.osutils.user_exists(self.username)
        m.AndReturn(False)

        n = self.osutils.create_user(self.username, mox.IsA(str))
        n.AndReturn((1, False))

        self.osutils.create_user_logon_session(self.username,
                                               mox.IsA(str),
                                               True)

        self.osutils.close_user_logon_session(None)
        self.osutils.add_user_to_local_group(self.username,
                                             self.group)

        self.mox.ReplayAll()
        response = self.svc.execute(self.service)
        self.mox.VerifyAll()
        self.assertEquals(response, (self.execution_done, False))

    def test_user_exists(self):
        m = factory.OSUtilsFactory.get_os_utils()
        m.AndReturn(self.osutils)

        m = httpservice.HttpService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = self.osutils.user_exists(self.username)
        m.AndReturn(True)

        self.osutils.add_user_to_local_group(self.username, self.group)

        self.osutils.set_user_password(self.username, mox.IsA(str))

        self.mox.ReplayAll()
        response = self.svc.execute(self.service)
        self.mox.VerifyAll()
        self.assertEquals(response, (self.execution_done, False))

    def test_create_user_multiple_groups(self):
        m = factory.OSUtilsFactory.get_os_utils()
        m.AndReturn(self.osutils)

        groups = ['Administrators', 'Users', 'Guests']

        m = httpservice.HttpService.get_meta_data(mox.IsA(str))
        m.AndReturn(self.json_metadata)

        m = self.osutils.user_exists(self.username)
        m.AndReturn(False)

        n = self.osutils.create_user(self.username, mox.IsA(str))
        n.AndReturn((1, False))

        self.osutils.create_user_logon_session(self.username, mox.IsA(str),
                                               True)

        self.osutils.close_user_logon_session(None)
        CONF.set_override('groups', groups)
        for group in groups:
            self.osutils.add_user_to_local_group(self.username, group)

        self.mox.ReplayAll()
        response = self.svc.execute(self.service)
        self.mox.VerifyAll()
        self.assertEquals(response, (self.execution_done, False))

    def test_user_exists_multiple_groups(self):
        m = factory.OSUtilsFactory.get_os_utils()
        m.AndReturn(self.osutils)

        groups = ['Administrators', 'Users', 'Guests']
        m = httpservice.HttpService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = self.osutils.user_exists(self.username)
        m.AndReturn(True)

        CONF.set_override('groups', groups)
        for group in groups:
            self.osutils.add_user_to_local_group(self.username, group)

        self.osutils.set_user_password(self.username, mox.IsA(str))

        self.mox.ReplayAll()
        response = self.svc.execute(self.service)
        self.mox.VerifyAll()
        self.assertEquals(response, (self.execution_done, False))
