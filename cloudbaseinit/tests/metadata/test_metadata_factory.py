# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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
from cloudbaseinit.utils import classloader
from cloudbaseinit.metadata import factory

CONF = cfg.CONF


class MetadataServiceFactoryTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.service = base.BaseMetadataService
        self.obj = factory.MetadataServiceFactory()

    def _setup_stubs(self):
        self.mox.StubOutWithMock(classloader.ClassLoader, 'load_class')
        self.mox.StubOutWithMock(base.BaseMetadataService, 'load')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_get_metadata_service(self):
        cl = classloader.ClassLoader()

        m = cl.load_class(mox.IsA(str))
        m.AndReturn(self.service)

        m = self.service.load()
        m.AndReturn(True)

        self.mox.ReplayAll()
        response = self.obj.get_metadata_service()
        self.mox.VerifyAll()
        self.assertIsInstance(response, self.service)

    def test_no_plugins_service(self):
        cl = classloader.ClassLoader()

        m = cl.load_class('wrong/path')
        m.AndRaise(Exception)

        self.mox.ReplayAll()
        self.assertRaises(Exception, self.obj.get_metadata_service)
        self.mox.VerifyAll()
