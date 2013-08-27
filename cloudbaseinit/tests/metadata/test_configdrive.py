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
import shutil
import unittest

from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.metadata.services.configdrive import manager
from cloudbaseinit.metadata.services.configdrive import configdrive


CONF = cfg.CONF


class ConfigDriveService(unittest.TestCase):

    def setUp(self):
        CONF.set_override('config_drive_raw_hhd', True)
        CONF.set_override('config_drive_cdrom', True)
        self.mox = mox.Mox()
        self.metadata_path = None
        self.target_path = 'dummy/path'
        self.mox.StubOutWithMock(
            manager.ConfigDriveManager, 'get_config_drive_files')
        self.svc = configdrive.ConfigDriveService()
        self.mox.StubOutWithMock(shutil, 'rmtree')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_load(self):
        manager.ConfigDriveManager.get_config_drive_files(
            mox.IsA(str), True, True).AndReturn(True)

        self.mox.ReplayAll()

        found = self.svc.load()

        self.mox.VerifyAll()

        self.assertTrue(found)

    def test_load_config_drive_files_found(self):
        manager.ConfigDriveManager.get_config_drive_files(
            mox.IsA(str), True, True).AndReturn(False)

        self.mox.ReplayAll()

        found = self.svc.load()

        self.mox.VerifyAll()

        self.assertFalse(found)

    def test_cleanup(self):
        self.svc._metadata_path = 'dummy/path'
        shutil.rmtree(mox.IgnoreArg(), True)

        self.mox.ReplayAll()

        self.svc.cleanup()

        self.mox.VerifyAll()

        self.assertEqual(self.svc._metadata_path, None)

    def test_cleanup_no_metadata_path(self):
        self.mox.ReplayAll()

        self.svc.cleanup()

        self.mox.VerifyAll()

        self.assertEqual(self.svc._metadata_path, None)
