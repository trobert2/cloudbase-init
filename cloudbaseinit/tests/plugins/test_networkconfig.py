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
import re

from cloudbaseinit.metadata.services import base as services_base
from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.osutils import windows
from cloudbaseinit.plugins import base as base_plugin
from cloudbaseinit.plugins.windows import networkconfig
from cloudbaseinit.tests.metadata import json_data

CONF = cfg.CONF


class NetworkConfigPluginTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.fake_data = 'fake'
        self.address = "iface eth0 inet static\\fake"
        self.netmask = "netmask\\fake"
        self.broadcast = "broadcast\\fake"
        self.gateway = "gateway\\fake"
        self.dns = 'dns\-nameservers\8.8.8.8'
        self.service = services_base.BaseMetadataService
        self.obj = networkconfig.NetworkConfigPlugin()
        self.json_metadata = json_data.get_fake_metadata_json('2013-04-04')
        self.cont_name = self.json_metadata['network_config']['content_path']

    def _setup_stubs(self):
        self.mox.StubOutWithMock(services_base.BaseMetadataService,
                                 'get_meta_data')
        self.mox.StubOutWithMock(services_base.BaseMetadataService,
                                 'get_content')
        self.mox.StubOutWithMock(re, 'search')
        self.mox.StubOutWithMock(windows.WindowsUtils,
                                 'set_static_network_config')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'get_network_adapters')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_network_config(self):
        CONF.set_override('network_adapter', 'fake network_adapter')
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = services_base.BaseMetadataService.get_content('openstack',
                                                          self.cont_name)
        m.AndReturn(self.fake_data)

        m = re.search(mox.IsA(str), mox.IsA(str))
        mock = self.mox.CreateMockAnything()
        m.AndReturn(mock)

        m = mock.group('address')
        m.AndReturn(self.address)

        m = mock.group('netmask')
        m.AndReturn(self.netmask)

        m = mock.group('broadcast')
        m.AndReturn(self.broadcast)

        m = mock.group('gateway')
        m.AndReturn(self.gateway)

        m = mock.group('dnsnameservers')
        dns = self.dns.strip().split(' ')
        m.AndReturn(self.dns)

        windows.WindowsUtils.set_static_network_config(
            CONF.network_adapter,
            self.address,
            self.netmask,
            self.broadcast,
            self.gateway, dns)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTION_DONE,
                                    None))

    def test_network_data_not_found(self):
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        json = self.json_metadata
        json['network_config'] = {}
        m.AndReturn(self.json_metadata)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTION_DONE,
                                    False))

    def test_format_not_recognized(self):
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = services_base.BaseMetadataService.get_content('openstack',
                                                          self.cont_name)
        m.AndReturn(self.fake_data)

        self.mox.ReplayAll()
        self.assertRaises(Exception, self.obj.execute, self.service)
        self.mox.VerifyAll()

    def test_network_adapter_name_not_specified(self):
        CONF.set_override('network_adapter', None)
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = services_base.BaseMetadataService.get_content('openstack',
                                                          self.cont_name)
        m.AndReturn(self.fake_data)

        m = re.search(mox.IsA(str), mox.IsA(str))
        mock = self.mox.CreateMockAnything()
        m.AndReturn(mock)

        m = mock.group('address')
        m.AndReturn(self.address)

        m = mock.group('netmask')
        m.AndReturn(self.netmask)

        m = mock.group('broadcast')
        m.AndReturn(self.broadcast)

        m = mock.group('gateway')
        m.AndReturn(self.gateway)

        m = mock.group('dnsnameservers')
        dns = self.dns.strip().split(' ')
        m.AndReturn(self.dns)

        network_adapter = 'f'
        m = windows.WindowsUtils.get_network_adapters()
        m.AndReturn(network_adapter)

        windows.WindowsUtils.set_static_network_config(network_adapter,
                                                       self.address,
                                                       self.netmask,
                                                       self.broadcast,
                                                       self.gateway, dns)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTION_DONE,
                                    None))

    def test_no_network_adapter_name(self):
        CONF.set_override('network_adapter', None)
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = services_base.BaseMetadataService.get_content('openstack',
                                                          self.cont_name)
        m.AndReturn(self.fake_data)

        m = re.search(mox.IsA(str), mox.IsA(str))
        mock = self.mox.CreateMockAnything()
        m.AndReturn(mock)

        m = mock.group('address')
        m.AndReturn(self.address)

        m = mock.group('netmask')
        m.AndReturn(self.netmask)

        m = mock.group('broadcast')
        m.AndReturn(self.broadcast)

        m = mock.group('gateway')
        m.AndReturn(self.gateway)

        m = mock.group('dnsnameservers')
        m.AndReturn(self.dns)

        m = windows.WindowsUtils.get_network_adapters()
        m.AndReturn('')

        self.mox.ReplayAll()
        self.assertRaises(Exception, self.obj.execute, self.service)
        self.mox.VerifyAll()
