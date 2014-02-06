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
import random
import string
import unittest

from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.plugins.windows import sethostname
from cloudbaseinit.tests.metadata import fake_json_response

CONF = cfg.CONF


class SetHostNamePluginPluginTests(unittest.TestCase):

    def random_string(self, length):
        chars = string.letters + string.digits
        newstring = ""
        for i in range(length):
            newstring = newstring + random.choice(chars)
        return newstring

    def setUp(self):
        self._sethostname_plugin = sethostname.SetHostNamePlugin()
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    @mock.patch('cloudbaseinit.osutils.factory.OSUtilsFactory.get_os_utils')
    def _test_execute(self, mock_get_os_utils, hostname_exists, new_hostname):
        mock_service = mock.MagicMock()
        mock_osutils = mock.MagicMock()
        fake_shared_data = 'fake data'
        self.fake_data['hostname'] = new_hostname
        mock_service.get_meta_data.return_value = self.fake_data
        CONF.set_override('netbios_host_name_compatibility', True)
        if hostname_exists is False:
            del self.fake_data['hostname']
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.set_host_name.return_value = False
        response = self._sethostname_plugin.execute(mock_service,
                                                    fake_shared_data)
        mock_service.get_meta_data.assert_called_once_with('openstack')
        if hostname_exists is True:
            length = sethostname.NETBIOS_HOST_NAME_MAX_LEN
            mock_get_os_utils.assert_called_once_with()
            hostname = self.fake_data['hostname'].split('.', 1)[0]
            if len(self.fake_data['hostname']) > length:
                hostname = hostname[:length]
            mock_osutils.set_host_name.assert_called_once_with(hostname)

        self.assertEqual(response, (1, False))

    def test_execute_hostname_to_be_truncated(self):
        length = sethostname.NETBIOS_HOST_NAME_MAX_LEN + 1
        new_hostname = self.random_string(length=length)
        self._test_execute(hostname_exists=True, new_hostname=new_hostname)

    def test_execute_no_truncate_needed(self):
        length = sethostname.NETBIOS_HOST_NAME_MAX_LEN - 1
        new_hostname = self.random_string(length=length)
        self._test_execute(hostname_exists=True, new_hostname=new_hostname)

    def test_execute_no_hostname(self):
        self._test_execute(hostname_exists=False,
                           new_hostname='fake_hostname')
