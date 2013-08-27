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

from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.metadata.services import base as services_base
from cloudbaseinit.osutils import windows
from cloudbaseinit.osutils import base as base_utils
from cloudbaseinit.plugins import base as base_plugin
from cloudbaseinit.plugins.windows import sshpublickeys
from cloudbaseinit.tests.metadata import json_data

CONF = cfg.CONF


class SetUserSSHPublicKeysPluginTest(unittest.TestCase):
    ''' testing user creation plugin '''

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.json_metadata = json_data.get_fake_metadata_json('2013-04-04')
        self.service = services_base.BaseMetadataService
        self.user_home = '%systemroot%\system32\config\systemprofile'
        self.user_ssh_dir = "%systemroot%\system32\config\systemprofile\.ssh"
        self.authorized_keys_path = \
            '%systemroot%\\system32\\config\\systemprofile\\' \
            '.ssh\\authorized_keys'
        self.obj = sshpublickeys.SetUserSSHPublicKeysPlugin()

    def _setup_stubs(self):
        self.mox.StubOutWithMock(services_base.BaseMetadataService,
                                 'get_meta_data')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'get_user_home')
        self.mox.StubOutWithMock(os.path, 'exists')
        self.mox.StubOutWithMock(os, 'makedirs')
        self.mox.StubOutWithMock(base_utils.BaseOSUtils, 'open_file')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_set_ssh_public_keys(self):
        CONF.username = 'Administrator'
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = windows.WindowsUtils.get_user_home(CONF.username)
        m.AndReturn(self.user_home)

        m = os.path.exists(self.user_ssh_dir)
        m.AndReturn(True)

        keys = self.json_metadata['public_keys']
        m = base_utils.BaseOSUtils.open_file(self.authorized_keys_path, 'w')
        handle = self.mox.CreateMockAnything()
        m.AndReturn(handle)
        handle.__enter__().AndReturn(handle)
        for key in keys:
            handle.write(keys[key])
        handle.__exit__(None, None, None).AndReturn(None)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTION_DONE, False))

    def test_no_public_keys(self):
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn((base_plugin.PLUGIN_EXECUTION_DONE, False))

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTION_DONE, False))

    def test_no_user_home(self):
        CONF.username = 'Admin'
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = windows.WindowsUtils.get_user_home(CONF.username)
        m.AndReturn(None)

        self.mox.ReplayAll()
        self.assertRaises(Exception, self.obj.execute, self.service)
        self.mox.VerifyAll()

    def test_no_ssh_path_found(self):
        CONF.username = 'Admin'
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = windows.WindowsUtils.get_user_home(CONF.username)
        m.AndReturn(self.user_home)

        m = os.path.exists(self.user_ssh_dir)
        m.AndReturn(False)

        m = os.makedirs(self.user_ssh_dir)
        m.AndReturn(True)
        keys = self.json_metadata['public_keys']
        m = base_utils.BaseOSUtils.open_file(self.authorized_keys_path, 'w')
        handle = self.mox.CreateMockAnything()
        m.AndReturn(handle)
        handle.__enter__().AndReturn(handle)
        for key in keys:
            handle.write(keys[key])
        handle.__exit__(None, None, None).AndReturn(None)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTION_DONE, False))
