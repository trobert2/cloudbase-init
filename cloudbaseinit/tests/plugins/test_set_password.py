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

from cloudbaseinit.metadata.services import base as services_base
from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.osutils import windows
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base as base_plugin
from cloudbaseinit.plugins.windows import setuserpassword
from cloudbaseinit.tests.metadata import json_data
from cloudbaseinit.utils import crypt

CONF = cfg.CONF


class SetUserPasswordPluginTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.obj = setuserpassword.SetUserPasswordPlugin()
        self.osutils = windows.WindowsUtils()
        self.version = self.obj._post_password_md_ver
        self.json = json_data.get_fake_metadata_json(self.version)
        self.key = self.json['public_keys']['name']
        self.password = 'Passw0rdfake!!'
        self.service = services_base.BaseMetadataService()

    def _setup_stubs(self):
        self.mox.StubOutWithMock(windows.WindowsUtils, 'user_exists')
        self.mox.StubOutWithMock(windows.WindowsUtils,
                                 'generate_random_password')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'set_user_password')
        self.mox.StubOutWithMock(osutils_factory.OSUtilsFactory,
                                 'get_os_utils')
        self.mox.StubOutWithMock(services_base.BaseMetadataService,
                                 'get_meta_data')
        self.mox.StubOutWithMock(services_base.BaseMetadataService,
                                 'post_password')
        self.mox.StubOutWithMock(services_base.BaseMetadataService,
                                 'is_password_set')
        self.mox.StubOutWithMock(services_base.BaseMetadataService,
                                 'can_post_password')
        self.mox.StubOutWithMock(crypt.CryptManager, 'load_ssh_rsa_public_key')
        self.mox.StubOutWithMock(crypt.RSAWrapper, 'public_encrypt')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_set_password(self):
        self.service.can_post_password = True
        CONF.username = 'Admin'

        m = osutils_factory.OSUtilsFactory.get_os_utils()
        m.AndReturn(self.osutils)

        m = self.service.is_password_set(self.version)
        m.AndReturn(False)

        m = self.osutils.user_exists(CONF.username)
        m.AndReturn(True)

        m = self.osutils.generate_random_password(14)
        m.AndReturn(self.password)

        m = self.service.get_meta_data('openstack',
                                       self.version)
        m.AndReturn(self.json)

        mock = self.mox.CreateMockAnything()
        m = crypt.CryptManager.load_ssh_rsa_public_key(self.key)
        m.AndReturn(mock)
        mock.__enter__().AndReturn(mock)
        mock.public_encrypt(self.password).AndReturn(self.password)
        mock.__exit__(None, None, None).AndReturn(None)

        m = self.service.post_password(mox.IsA(str), self.version)
        m.AndReturn(True)

        self.osutils.set_user_password(CONF.username, self.password)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTE_ON_NEXT_BOOT,
                                    False))

    def test_password_is_set(self):
        CONF.username = 'Admin'
        self.service.can_post_password = True

        m = self.service.is_password_set(self.version)
        m.AndReturn(True)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTE_ON_NEXT_BOOT,
                                    False))

    def test_cannot_post_password(self):
        CONF.username = 'Admin'
        self.service.can_post_password = False

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response,
                         (base_plugin.PLUGIN_EXECUTION_DONE,
                          False))

    def test_user_not_existent(self):
        m = osutils_factory.OSUtilsFactory.get_os_utils()
        m.AndReturn(self.osutils)

        self.service.can_post_password = True
        CONF.username = 'Admin'

        m = self.service.is_password_set(self.version)
        m.AndReturn(False)

        m = self.osutils.user_exists(CONF.username)
        m.AndReturn(False)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTE_ON_NEXT_BOOT,
                                    False))

    def test_no_public_keys(self):
        m = osutils_factory.OSUtilsFactory.get_os_utils()
        m.AndReturn(self.osutils)

        self.service.can_post_password = True
        CONF.username = 'Admin'

        m = self.service.is_password_set(self.version)
        m.AndReturn(False)

        m = self.osutils.user_exists(CONF.username)
        m.AndReturn(True)

        m = self.osutils.generate_random_password(14)
        m.AndReturn(self.password)
        self.osutils.set_user_password(CONF.username, self.password)

        json = self.json
        json['public_keys'] = {}
        m = self.service.get_meta_data('openstack', self.version)
        m.AndReturn(json)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTE_ON_NEXT_BOOT,
                                    False))
