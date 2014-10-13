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

import importlib
import mock
import unittest


class WindowsSecurityUtilsTests(unittest.TestCase):

    def setUp(self):
        self._moves_mock = mock.MagicMock()
        self._mock_osutils = mock.MagicMock()

        self._module_patcher = mock.patch.dict(
            'sys.modules',
            {'six.moves': self._moves_mock})

        self._module_patcher.start()
        self._winreg_mock = self._moves_mock.winreg

        self.security = importlib.import_module(
            "cloudbaseinit.utils.windows.security")
        self.security.WindowsError = mock.MagicMock()

        self._security_utils = self.security.WindowsSecurityUtils(
            self._mock_osutils)

    def test_set_local_account_token_filter_policy(self):
        self._security_utils.set_local_account_token_filter_policy(enable=True)

        self._mock_osutils._set_reg_key.assert_called_once_with(
            self._security_utils._uac_key,
            self._security_utils._uac_value_name, int(True))

    def _test_get_local_account_token_filter_policy(self, ret_value):
        if ret_value:
            self._winreg_mock.OpenKey.side_effect = [
                self.security.WindowsError]
        else:
            self._winreg_mock.QueryValueEx.return_value = (
                mock.sentinel.value, mock.sentinel.regtype)

        response = self._security_utils.get_local_account_token_filter_policy()

        self._winreg_mock.QueryValueEx.assert_called_once_with(
            self._winreg_mock.OpenKey.return_value.__enter__(),
            self._security_utils._uac_value_name)

        self._winreg_mock.OpenKey.assert_called_once_with(
            self._winreg_mock.HKEY_LOCAL_MACHINE,
            self._security_utils._uac_key)

        if ret_value is self.security.WindowsError:
            print response
            self.assertTrue(not response)

        else:
            self.assertEqual(mock.sentinel.value, response)

    def test_get_local_account_token_filter_policy(self):
        self._test_get_local_account_token_filter_policy(ret_value=None)

    # def test_get_local_account_token_filter_policy_windows_error(self):
    #     self._test_get_local_account_token_filter_policy(
    #         ret_value=self.security.WindowsError)
