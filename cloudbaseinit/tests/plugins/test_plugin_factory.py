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

from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.plugins import factory
from cloudbaseinit.plugins.windows import createuser
from cloudbaseinit.plugins.windows import extendvolumes
from cloudbaseinit.plugins.windows import networkconfig
from cloudbaseinit.plugins.windows import sethostname
from cloudbaseinit.plugins.windows import setuserpassword
from cloudbaseinit.plugins.windows import sshpublickeys
from cloudbaseinit.plugins.windows import userdata
from cloudbaseinit.utils import classloader

CONF = cfg.CONF


class PluginFactoryTest(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self._setup_stubs()

        self.obj = factory.PluginFactory()

    def _setup_stubs(self):
        self.mox.StubOutWithMock(classloader.ClassLoader, 'load_class')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_load_plugins(self):
        CONF.set_override('plugins', [createuser.CreateUserPlugin,
                                      extendvolumes.ExtendVolumesPlugin,
                                      networkconfig.NetworkConfigPlugin,
                                      sethostname.SetHostNamePlugin,
                                      setuserpassword.SetUserPasswordPlugin,
                                      sshpublickeys.SetUserSSHPublicKeysPlugin,
                                      userdata.UserDataPlugin])
        cl = classloader.ClassLoader()

        for foo in CONF.plugins:
            m = cl.load_class(foo)
            m.AndReturn(foo)

        self.mox.ReplayAll()
        response = self.obj.load_plugins()
        self.mox.VerifyAll()
        i = 0
        for instance in response:
            self.assertIsInstance(instance, CONF.plugins[i])
            i += 1
