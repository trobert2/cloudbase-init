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

from cloudbaseinit.plugins.windows import sethostname
from cloudbaseinit.plugins.windows import createuser
from cloudbaseinit.plugins.windows import networkconfig
from cloudbaseinit.plugins.windows import sshpublickeys
from cloudbaseinit.plugins.windows import extendvolumes
from cloudbaseinit.plugins.windows import userdata
from cloudbaseinit.plugins.windows import setuserpassword
from cloudbaseinit import init
from cloudbaseinit.metadata import factory as metadata_factory
from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.osutils import windows
from cloudbaseinit.plugins import base as base_plugin
from cloudbaseinit.metadata.services import httpservice
from cloudbaseinit.plugins import factory as plugin_factory

CONF = cfg.CONF


class InitManagerTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.data_type = 'openstack'
        self.instance_id = 'fake instance 00001'
        self.obj = init.InitManager()
        self.version = 'latest'

        CONF.set_override('plugins', [createuser.CreateUserPlugin,
                                      extendvolumes.ExtendVolumesPlugin,
                                      networkconfig.NetworkConfigPlugin,
                                      sethostname.SetHostNamePlugin,
                                      setuserpassword.SetUserPasswordPlugin,
                                      sshpublickeys.SetUserSSHPublicKeysPlugin,
                                      userdata.UserDataPlugin])
        self.service = httpservice.HttpService()
        self.status = 1

    def _setup_stubs(self):
        self.mox.StubOutWithMock(base_plugin.BasePlugin, 'get_name')
        self.mox.StubOutWithMock(base_plugin.BasePlugin, 'get_os_requirements')
        self.mox.StubOutWithMock(extendvolumes.ExtendVolumesPlugin,
                                 'get_os_requirements')

        self.mox.StubOutWithMock(sethostname.SetHostNamePlugin, 'execute')
        self.mox.StubOutWithMock(createuser.CreateUserPlugin, 'execute')
        self.mox.StubOutWithMock(networkconfig.NetworkConfigPlugin, 'execute')
        self.mox.StubOutWithMock(sshpublickeys.SetUserSSHPublicKeysPlugin,
                                 'execute')
        self.mox.StubOutWithMock(extendvolumes.ExtendVolumesPlugin, 'execute')
        self.mox.StubOutWithMock(userdata.UserDataPlugin, 'execute')
        self.mox.StubOutWithMock(setuserpassword.SetUserPasswordPlugin,
                                 'execute')

        self.mox.StubOutWithMock(metadata_factory.MetadataServiceFactory,
                                 'get_metadata_service')
        self.mox.StubOutWithMock(plugin_factory.PluginFactory, 'load_plugins')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'get_config_value')
        self.mox.StubOutWithMock(httpservice.HttpService, 'get_instance_id')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'set_config_value')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'reboot')
        self.mox.StubOutWithMock(windows.WindowsUtils, 'terminate')

    def tearDown(self):
        self.mox.UnsetStubs()

    def _test_config_host(self, reg_instance, reg_status=None):
        mdsf = metadata_factory.MetadataServiceFactory()

        m = plugin_factory.PluginFactory.load_plugins()
        m.AndReturn(CONF.plugins)

        m = mdsf.get_metadata_service()
        m.AndReturn(self.service)

        m = windows.WindowsUtils.get_config_value('instance_id',
                                                  'Instance')
        m.AndReturn(reg_instance)

        check = httpservice.HttpService.get_instance_id(self.data_type,
                                                        self.version)
        check.AndReturn(self.instance_id)
        if reg_instance is not self.instance_id:
            m = windows.WindowsUtils.set_config_value('instance_id',
                                                      self.instance_id,
                                                      'Instance')
            m.AndReturn(None)
        i = 0
        for plugin in CONF.plugins:
            m = base_plugin.BasePlugin.get_name()
            m.AndReturn(str(CONF.plugins[i]))

            m = plugin.get_os_requirements()
            m.AndReturn((None, None))

            m = base_plugin.BasePlugin.get_name()
            m.AndReturn(str(CONF.plugins[i]))

            m = windows.WindowsUtils.get_config_value(mox.IsA(str),
                                                      'Plugins')
            m.AndReturn(reg_status)

            if not reg_status:
                m = plugin.execute(self.service)
                m.AndReturn((base_plugin.PLUGIN_EXECUTION_DONE,
                             True))
                m = windows.WindowsUtils.set_config_value(mox.IsA(str), 1,
                                                          'Plugins')
                m.AndReturn(None)
                i += 1
            else:
                i += 1
        if not reg_status:
            windows.WindowsUtils.reboot()
        elif reg_status == 1:
            windows.WindowsUtils.terminate()

        self.mox.ReplayAll()
        response = self.obj.configure_host()
        self.mox.VerifyAll()
        self.assertEqual(response, None)

    def test_config_host_different_instance_id(self):
        self._test_config_host(reg_instance='fake instance 0')

    def test_config_host_no_instance_id(self):
        self._test_config_host(reg_instance=None)

    def test_config_host_execution_done(self):
        self._test_config_host(reg_instance=self.instance_id, reg_status=1)

    def test_config_host_execute_same_instance(self):
        self._test_config_host(reg_instance=self.instance_id, reg_status=None)
