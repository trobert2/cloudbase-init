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
from cloudbaseinit.plugins import base as base_plugin
from cloudbaseinit.plugins.windows import extendvolumes
from cloudbaseinit.plugins.windows import vds

CONF = cfg.CONF


class ExtendVolumesPluginTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.obj = extendvolumes.ExtendVolumesPlugin()
        self.swproviders = vds.VDS_QUERY_SOFTWARE_PROVIDERS

    def _setup_stubs(self):
        self.mox.StubOutWithMock(vds, 'load_vds_service')
        self.mox.StubOutWithMock(extendvolumes.ExtendVolumesPlugin,
                                 '_query_providers')
        self.mox.StubOutWithMock(extendvolumes.ExtendVolumesPlugin,
                                 '_query_packs')
        self.mox.StubOutWithMock(extendvolumes.ExtendVolumesPlugin,
                                 '_extend_volumes')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_extend_volumes(self):
        prov1 = self.mox.CreateMockAnything()
        prov2 = self.mox.CreateMockAnything()
        providers = [prov1, prov2]
        pack1 = self.mox.CreateMockAnything()
        pack2 = self.mox.CreateMockAnything()
        packs = [pack1, pack2]
        CONF.volumes_to_extend=[1]
        m = vds.load_vds_service()
        svc = self.mox.CreateMockAnything()
        m.AndReturn(svc)

        m = extendvolumes.ExtendVolumesPlugin._query_providers(svc)
        m.AndReturn(providers)

        for provider in providers:
            m = extendvolumes.ExtendVolumesPlugin._query_packs(provider)
            m.AndReturn(packs)
            for pack in packs:
                extendvolumes.ExtendVolumesPlugin._extend_volumes(pack,
                                                        CONF.volumes_to_extend)

        self.mox.ReplayAll()
        response = self.obj.execute(services_base.BaseMetadataService)
        self.mox.VerifyAll()
        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTE_ON_NEXT_BOOT,
                                    False))
