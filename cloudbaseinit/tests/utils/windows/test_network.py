# Copyright 2014 Cloudbase Solutions Srl
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

import unittest

from oslo.config import cfg

from cloudbaseinit.utils.windows import network

CONF = cfg.CONF


class WindowsNetworkUtilsTests(unittest.TestCase):

    def test_format_mac_address(self):
        phys_address = [00, 00, 00, 00]
        response = network._format_mac_address(phys_address=phys_address,
                                               phys_address_len=4)
        self.assertEqual(response, "00:00:00:00")

    def test_socket_addr_to_str(self):
        pass
        # response = network._socket_addr_to_str()