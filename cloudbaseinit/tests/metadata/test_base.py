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

from cloudbaseinit.metadata.services import base
from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.tests.metadata import json_data

CONF = cfg.CONF


class BaseMetadataServiceTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.version = 'latest'
        self.svc = base.BaseMetadataService()
        self.fake_meta_data = json_data.get_fake_metadata_json('2013-04-04')
        self.data_type = 'openstack'

    def _setup_stubs(self):
        self.mox.StubOutWithMock(base.BaseMetadataService, '_get_cache_data')
        self.mox.StubOutWithMock(base.BaseMetadataService, '_post_data')
        self.mox.StubOutWithMock(base.BaseMetadataService, '_get_data')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_get_cache_meta_data(self):
        metadata_path = 'openstack/latest/meta_data.json'
        m = base.BaseMetadataService._get_cache_data(metadata_path)
        m.AndReturn(self.fake_meta_data)

        self.mox.ReplayAll()
        meta_data = self.svc.get_meta_data(self.data_type, self.version)
        self.mox.VerifyAll()
        self.assertEqual(meta_data, self.fake_meta_data)

    def test_get_user_data(self):
        userdata_path = 'openstack/latest/user_data'
        m = base.BaseMetadataService._get_cache_data(userdata_path)
        m.AndReturn(self.fake_meta_data)

        self.mox.ReplayAll()
        meta_data = self.svc.get_user_data(self.data_type, self.version)
        self.mox.VerifyAll()
        self.assertEqual(meta_data, self.fake_meta_data)

    def test_get_content(self):
        content_path = 'openstack/content/latest'
        m = base.BaseMetadataService._get_cache_data(content_path)
        m.AndReturn(self.fake_meta_data)

        self.mox.ReplayAll()
        meta_data = self.svc.get_content(self.data_type, self.version)
        self.mox.VerifyAll()
        self.assertEqual(meta_data, self.fake_meta_data)

    def test_post_password(self):
        CONF.set_override('retry_count', 0)
        password_path = 'openstack/latest/password'
        password = 'password'

        m = self.svc._post_data(password_path, password)
        m.AndRaise(base.NotExistingMetadataException)

        self.mox.ReplayAll()
        self.assertRaises(base.NotExistingMetadataException,
                          self.svc.post_password,
                          password, self.version)
        self.mox.VerifyAll()

    def test_is_password_set(self):
        password_path = 'openstack/latest/password'
        password = 'password'

        m = base.BaseMetadataService._get_data(password_path)
        m.AndReturn(password)

        self.mox.ReplayAll()
        password_check = self.svc.is_password_set(self.version)
        self.mox.VerifyAll()
        self.assertTrue(password_check)
