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
from cloudbaseinit.plugins import base as base_plugin
from cloudbaseinit.plugins.windows import sethostname
from cloudbaseinit.tests.metadata import json_data

CONF = cfg.CONF


class SetHostNamePluginTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()
        self.json_metadata = json_data.get_fake_metadata_json('2013-04-04')
        self.new_host_name = self.json_metadata['hostname'].split('.', 1)[0]
        self.obj = sethostname.SetHostNamePlugin()
        self.service = services_base.BaseMetadataService

    def _setup_stubs(self):
        self.mox.StubOutWithMock(services_base.BaseMetadataService,
                                 'get_meta_data')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'set_host_name')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_set_hostname(self):
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        m.AndReturn(self.json_metadata)

        m = windows.WindowsUtils.set_host_name(self.new_host_name)
        m.AndReturn(True)

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTION_DONE, True))

    def test_hostname_not_in_metadata(self):
        m = services_base.BaseMetadataService.get_meta_data('openstack')
        json = self.json_metadata
        json['hostname'] = ''
        m.AndReturn((base_plugin.PLUGIN_EXECUTION_DONE, False))

        self.mox.ReplayAll()
        response = self.obj.execute(self.service)
        self.mox.VerifyAll()

        self.assertEqual(response, (base_plugin.PLUGIN_EXECUTION_DONE, False))
