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

import mock
import os
import unittest

from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.osutils import windows
from cloudbaseinit.osutils import factory
from cloudbaseinit.plugins import base as base_plugin
from cloudbaseinit.plugins.windows import sshpublickeys
from cloudbaseinit.tests.metadata import json_data


CONF = cfg.CONF


class SetUserSSHPublicKeysPluginTest(unittest.TestCase):
    ''' testing plugin for manipulation of ssh public keys'''

    _JSON_METADATA = json_data.get_fake_metadata_json('2013-04-04')
    _USER_HOME = 'fake\system32\config\systemprofile'
    _USER_SSH_DIR = "fake\system32\config\systemprofile\.ssh"
    _AUTHORIZED_KEY_PATH = 'fake\\system32\\config\\systemprofile\\' \
                           '.ssh\\authorized_keys'
    CONF.username = 'Administrator'

    def setUp(self):
        self._ssh = sshpublickeys.SetUserSSHPublicKeysPlugin()
        self.service = mock.MagicMock()
        self._winutils = windows.WindowsUtils()

    def _test_set_ssh_public_keys(self, data, home, path_exists=True):
        self.service.get_meta_data = mock.MagicMock(
            return_value=self._JSON_METADATA)

        factory.OSUtilsFactory.get_os_utils = mock.MagicMock(
            return_value=self._winutils)
        self._winutils.get_user_home = mock.MagicMock(return_value=home)
        if not home:
            self.assertRaises(Exception, self._ssh.execute, self.service)
        else:
            if not data:
                empty = []
                self.service.get_meta_data = mock.MagicMock(
                    return_value=empty)
                response = self._ssh.execute(self.service)
                self.assertEqual(response,
                                 (base_plugin.PLUGIN_EXECUTION_DONE, False))
            elif data:
                self.service.get_meta_data = mock.MagicMock(
                    return_value=self._JSON_METADATA)
                os.makedirs = mock.MagicMock()
                side_effect = lambda v1, v2: v1+'\\'+v2
                os.path.join = mock.MagicMock(side_effect=side_effect)
                os.path.exists = mock.MagicMock(return_value=path_exists)

                with mock.patch('cloudbaseinit.plugins.windows.sshpublickeys'
                                '.open', mock.mock_open(), create=True):
                    response = self._ssh.execute(self.service)
                if not path_exists:
                    os.makedirs.assert_called_with(self._USER_SSH_DIR)
                self.service.get_meta_data.assert_called_with('openstack')
                factory.OSUtilsFactory.get_os_utils.assert_called_once_with()

                self.assertTrue(os.path.join.call_count == 2)
                self.assertEqual(response,
                                 (base_plugin.PLUGIN_EXECUTION_DONE, False))

    def test_set_ssh_public_keys(self):
        self._test_set_ssh_public_keys(True, self._USER_HOME)

    def test_set_ssh_public_keys_no_home(self):
        self._test_set_ssh_public_keys(True, None)

    def test_set_ssh_public_keys_no_keys(self):
        self._test_set_ssh_public_keys(False, self._USER_HOME)

    def test_set_ssh_public_keys_no_path(self):
        self._test_set_ssh_public_keys(True, self._USER_HOME, False)
