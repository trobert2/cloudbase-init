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

import ctypes
import mock
import os
import time
import sys
import unittest

from oslo.config import cfg

if sys.platform == 'win32':
    import _winreg
    import win32process
    import win32security
    import wmi

    from ctypes import windll
    from ctypes import wintypes

from cloudbaseinit.osutils import windows as windows_utils

CONF = cfg.CONF

_ctypes_mock = mock.MagicMock()
mock_dict = {'ctypes': _ctypes_mock}

# @unittest.skipUnless(sys.platform == "win32", "requires Windows")
class WindowsUtilsTest(unittest.TestCase):
    '''Tests for the windows utils class'''

    _CONFIG_NAME = 'FakeConfig'
    _DESTINATION = '192.168.192.168'
    _GATEWAY = '10.7.1.1'
    _NETMASK = '255.255.255.0'
    _PASSWORD = 'Passw0rd'
    _SECTION = 'fake_section'
    _USERNAME = 'Admin'

    @mock.patch.dict(sys.modules, mock_dict)
    def setUp(self):
        windows_utils.wintypes = mock.MagicMock()
        windows_utils.windll = mock.MagicMock()
        windows_utils.advapi32 = mock.MagicMock()

        self._winutils = windows_utils.WindowsUtils()
        self._conn = mock.MagicMock()

    def test_enable_shutdown_privilege(self):
        fake_process = mock.MagicMock()
        fake_token = True
        private_LUID = 'fakeid'
        win32process.GetCurrentProcess = mock.MagicMock(
            return_value=fake_process)
        win32security.OpenProcessToken = mock.MagicMock(
            return_value=fake_token)
        win32security.LookupPrivilegeValue = mock.MagicMock(
            return_value=private_LUID)
        win32security.AdjustTokenPrivileges = mock.MagicMock()
        self._winutils._enable_shutdown_privilege()
        privilege = [(private_LUID, win32security.SE_PRIVILEGE_ENABLED)]
        win32security.AdjustTokenPrivileges.assert_called_with(
            fake_token,
            False,
            privilege)

        win32security.OpenProcessToken.assert_called_with(
            fake_process,
            win32security.TOKEN_ADJUST_PRIVILEGES |
            win32security.TOKEN_QUERY)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._enable_shutdown_privilege')
    def _test_reboot(self, mock_enable_shutdown_privilege, ret_value):
        windll.advapi32.InitiateSystemShutdownW = mock.MagicMock(
            return_value=ret_value)

        if not ret_value:
            self.assertRaises(Exception, self._winutils.reboot)
        else:
            self._winutils.reboot()

            windll.advapi32.InitiateSystemShutdownW.assert_called_with(
                0,
                "Cloudbase-Init reboot",
                0, True, True)

    def test_reboot(self):
        self._test_reboot(ret_value=True)

    def test_reboot_failed(self):
        self._test_reboot(ret_value=None)

    @mock.patch('wmi.WMI')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._sanitize_wmi_input')
    def _test_get_user_wmi_object(self, mock_sanitize_wmi_input, mock_WMI,
                                  returnvalue):
        mock_WMI.return_value = self._conn
        mock_sanitize_wmi_input.return_value = self._USERNAME
        self._conn.query.return_value = returnvalue
        response = self._winutils._get_user_wmi_object(self._USERNAME)
        self._conn.query.assert_called_with("SELECT * FROM Win32_Account "
                                            "where name = \'%s\'" %
                                            self._USERNAME)
        mock_sanitize_wmi_input.assert_called_with(self._USERNAME)
        mock_WMI.assert_called_with(moniker='//./root/cimv2')
        if returnvalue:
            self.assertTrue(response is not None)
        else:
            self.assertTrue(response is None)

    def test_get_user_wmi_object(self):
        caption = 'fake'
        self._test_get_user_wmi_object(returnvalue=caption)

    def test_no_user_wmi_object(self):
        empty_caption = ''
        self._test_get_user_wmi_object(returnvalue=empty_caption)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_user_wmi_object')
    def _test_user_exists(self, mock_get_user_wmi_object, returnvalue):
        mock_get_user_wmi_object.return_value = returnvalue
        response = self._winutils.user_exists(returnvalue)
        mock_get_user_wmi_object.assert_called_with(returnvalue)
        if returnvalue:
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_user_exists(self):
        self._test_user_exists(returnvalue=self._USERNAME)

    def test_username_does_not_exist(self):
        self._test_user_exists(returnvalue=None)

    def test_sanitize_wmi_input(self):
        unsanitised = ' \' '
        response = self._winutils._sanitize_wmi_input(unsanitised)
        sanitised = ' \'\' '
        self.assertEqual(response, sanitised)

    def test_sanitize_shell_input(self):
        unsanitised = ' " '
        response = self._winutils.sanitize_shell_input(unsanitised)
        sanitised = ' \\" '
        self.assertEqual(response, sanitised)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._set_user_password_expiration')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.execute_process')
    def _test_create_or_change_user(self, mock_execute_process,
                                    mock_set_user_password_expiration,
                                    create, password_expires, ret_value=0):
        args = ['NET', 'USER', self._USERNAME, self._PASSWORD]
        if create:
            args.append('/ADD')
        mock_execute_process.return_value = (None, None, ret_value)
        if not ret_value:
            self._winutils._create_or_change_user(self._USERNAME,
                                                  self._PASSWORD, create,
                                                  password_expires)
            mock_set_user_password_expiration.assert_called_with(
                self._USERNAME, password_expires)
        else:
            self.assertRaises(
                Exception, self._winutils._create_or_change_user,
                self._USERNAME, self._PASSWORD, create, password_expires)
        mock_execute_process.assert_called_with(args)

    def test_create_user_and_add_password_expire_true(self):
        self._test_create_or_change_user(create=True, password_expires=True)

    def test_create_user_and_add_password_expire_false(self):
        self._test_create_or_change_user(create=True, password_expires=False)

    def test_add_password_expire_true(self):
        self._test_create_or_change_user(create=False, password_expires=True)

    def test_add_password_expire_false(self):
        self._test_create_or_change_user(create=False, password_expires=False)

    def test_create_user_and_add_password_expire_true_with_ret_value(self):
        self._test_create_or_change_user(create=True, password_expires=True,
                                         ret_value=1)

    def test_create_user_and_add_password_expire_false_with_ret_value(self):
        self._test_create_or_change_user(create=True,
                                         password_expires=False, ret_value=1)

    def test_add_password_expire_true_with_ret_value(self):
        self._test_create_or_change_user(create=False,
                                         password_expires=True, ret_value=1)

    def test_add_password_expire_false_with_ret_value(self):
        self._test_create_or_change_user(create=False,
                                         password_expires=False, ret_value=1)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_user_wmi_object')
    def _test_set_user_password_expiration(self, mock_get_user_wmi_object,
                                           fake_obj):
        mock_get_user_wmi_object.return_value = fake_obj
        response = self._winutils._set_user_password_expiration(
            self._USERNAME, True)
        if fake_obj:
            self.assertTrue(fake_obj.PasswordExpires)
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_set_password_expiration(self):
        fake = mock.Mock()
        self._test_set_user_password_expiration(fake_obj=fake)

    def test_set_password_expiration_no_object(self):
        self._test_set_user_password_expiration(fake_obj=None)

    @mock.patch.object(ctypes, "sizeof")
    @mock.patch.object(ctypes, "create_string_buffer")
    @mock.patch.object(ctypes, "create_unicode_buffer")
    @mock.patch.object(ctypes, "byref")
    def _test_get_user_sid_and_domain(self, mock_byref,
                                      mock_create_unicode_buffer,
                                      mock_create_string_buffer,
                                      mock_sizeof, ret_val):
        cbSid = mock.Mock()
        sid = mock.Mock()
        size = 1024
        cchReferencedDomainName = mock.Mock()
        domainName = mock.Mock()

        mock_create_string_buffer.return_value = sid
        mock_sizeof.return_value = size

        windows_utils.wintypes.DWORD.return_value = cchReferencedDomainName
        mock_create_unicode_buffer.return_value = domainName

        windows_utils.windll.advapi32.LookupAccountNameW.return_value = ret_val
        if ret_val is None:
            self.assertRaises(
                Exception, self._winutils._get_user_sid_and_domain,
                self._USERNAME)
        else:
            response = self._winutils._get_user_sid_and_domain(self._USERNAME)

            windows_utils.advapi32.LookupAccountNameW.assert_called_with(
                0, unicode(self._USERNAME), sid, mock_byref.return_value,
                domainName, mock_byref.return_value,
                mock_byref.return_value)
            self.assertEqual(response, (sid, domainName.value))

    def test_get_user_sid_and_domain(self):
        fake_obj = mock.Mock()
        self._test_get_user_sid_and_domain(ret_val=fake_obj)

    def test_get_user_sid_and_domain_no_return_value(self):
        self._test_get_user_sid_and_domain(ret_val=None)

    def _test_add_user_to_local_group(self, ret_value):
        windows_utils.Win32_LOCALGROUP_MEMBERS_INFO_3 = mock.MagicMock()
        lmi = windows_utils.Win32_LOCALGROUP_MEMBERS_INFO_3()
        group_name = 'Admins'

        windll.netapi32.NetLocalGroupAddMembers = mock.MagicMock(
            return_value=ret_value)

        if ret_value is not 0:
            self.assertRaises(
                Exception, self._winutils.add_user_to_local_group,
                self._USERNAME, group_name)
        else:
            ctypes.addressof = mock.MagicMock()
            self._winutils.add_user_to_local_group(self._USERNAME,
                                                   group_name)
            windll.netapi32.NetLocalGroupAddMembers.assert_called_with(
                0, unicode(group_name), 3, ctypes.addressof(lmi), 1)
            self.assertEqual(lmi.lgrmi3_domainandname, unicode(self._USERNAME))

    def test_add_user_to_local_group_no_error(self):
        self._test_add_user_to_local_group(ret_value=0)

    def test_add_user_to_local_group_not_found(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.NERR_GroupNotFound)

    def test_add_user_to_local_group_access_denied(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.ERROR_ACCESS_DENIED)

    def test_add_user_to_local_group_no_member(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.ERROR_NO_SUCH_MEMBER)

    def test_add_user_to_local_group_member_in_alias(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.ERROR_MEMBER_IN_ALIAS)

    def test_add_user_to_local_group_invalid_member(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.ERROR_INVALID_MEMBER)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_user_wmi_object')
    def _test_get_user_sid(self, mock_get_user_wmi_object, fail):
        r = mock.Mock()
        if not fail:
            mock_get_user_wmi_object.return_value = None
            response = self._winutils.get_user_sid(self._USERNAME)
            self.assertTrue(response is None)
        else:
            mock_get_user_wmi_object.return_value = r
            response = self._winutils.get_user_sid(self._USERNAME)
            self.assertTrue(response is not None)
        mock_get_user_wmi_object.assert_called_with(self._USERNAME)

    def test_get_user_sid(self):
        self._test_get_user_sid(fail=False)

    def test_get_user_sid_fail(self):
        self._test_get_user_sid(fail=True)

    def _test_create_user_logon_session(self, logon, loaduser,
                                        load_profile=True):
        wintypes.HANDLE = mock.MagicMock()
        pi = windows_utils.Win32_PROFILEINFO()
        windll.advapi32.LogonUserW = mock.MagicMock(return_value=logon)
        ctypes.byref = mock.MagicMock()

        if not logon:
            self.assertRaises(
                Exception, self._winutils.create_user_logon_session,
                self._USERNAME, self._PASSWORD, domain='.',
                load_profile=load_profile)

        elif load_profile and not loaduser:
            windll.userenv.LoadUserProfileW = mock.MagicMock(
                return_value=None)
            windll.kernel32.CloseHandle = mock.MagicMock(return_value=None)
            self.assertRaises(Exception,
                              self._winutils.create_user_logon_session,
                              self._USERNAME, self._PASSWORD, domain='.',
                              load_profile=load_profile)

            windll.userenv.LoadUserProfileW.assert_called_with(
                wintypes.HANDLE(), ctypes.byref(pi))
            windll.kernel32.CloseHandle.assert_called_with(wintypes.HANDLE())

        elif not load_profile:
            response = self._winutils.create_user_logon_session(
                self._USERNAME, self._PASSWORD, domain='.',
                load_profile=load_profile)
            self.assertTrue(response is not None)
        else:
            size = 1024
            windll.userenv.LoadUserProfileW = mock.MagicMock()
            ctypes.sizeof = mock.MagicMock(return_value=size)
            windows_utils.Win32_PROFILEINFO = mock.MagicMock(
                return_value=loaduser)

            response = self._winutils.create_user_logon_session(
                self._USERNAME, self._PASSWORD, domain='.',
                load_profile=load_profile)

            windll.userenv.LoadUserProfileW.assert_called_with(
                wintypes.HANDLE(), ctypes.byref(pi))
            self.assertTrue(response is not None)

    def test_create_user_logon_session_fail_load_false(self):
        self._test_create_user_logon_session(0, 0, True)

    def test_create_user_logon_session_fail_load_true(self):
        self._test_create_user_logon_session(0, 0, False)

    def test_create_user_logon_session_load_true(self):
        m = mock.Mock()
        n = mock.Mock()
        self._test_create_user_logon_session(m, n, True)

    def test_create_user_logon_session_load_false(self):
        m = mock.Mock()
        n = mock.Mock()
        self._test_create_user_logon_session(m, n, False)

    def test_create_user_logon_session_no_load_true(self):
        m = mock.Mock()
        self._test_create_user_logon_session(m, None, True)

    def test_create_user_logon_session_no_load_false(self):
        m = mock.Mock()
        self._test_create_user_logon_session(m, None, False)

    def test_close_user_logon_session(self):
        token = mock.Mock()
        windll.kernel32.CloseHandle = mock.MagicMock()
        self._winutils.close_user_logon_session(token)
        windll.kernel32.CloseHandle.assert_called_with(token)

    @mock.patch('ctypes.windll.kernel32.SetComputerNameExW')
    def _test_set_host_name(self, mock_SetComputerNameExW, ret_value):
        mock_SetComputerNameExW.return_value = ret_value
        if not ret_value:
            self.assertRaises(Exception, self._winutils.set_host_name,
                              'fake name')
        else:
            self._winutils.set_host_name('fake name')
        mock_SetComputerNameExW.assert_called_with(
            self._winutils.ComputerNamePhysicalDnsHostname,
            unicode('fake name'))

    def test_set_host_name(self):
        self._test_set_host_name(ret_value='fake response')

    def test_set_host_exception(self):
        self._test_set_host_name(ret_value=None)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_user_sid')
    def _test_get_user_home(self, mock_get_user_sid, user_sid):
        key = mock.MagicMock()
        mock_get_user_sid.return_value = user_sid
        _winreg.OpenKey = mock.MagicMock(return_value=key)
        _winreg.QueryValueEx = mock.MagicMock()
        response = self._winutils.get_user_home(self._USERNAME)
        if user_sid:
            mock_get_user_sid.assert_called_with(self._USERNAME)
            _winreg.OpenKey.assert_called_with(
                _winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows '
                                            'NT\\CurrentVersion\\ProfileList\\'
                                            '%s' % mock_get_user_sid())
            self.assertTrue(response is not None)
            _winreg.QueryValueEx.assert_called_with(
                _winreg.OpenKey().__enter__(), 'ProfileImagePath')
        else:
            self.assertTrue(response is None)

    def test_get_user_home(self):
        user = mock.MagicMock()
        self._test_get_user_home(user_sid=user)

    def test_get_user_home_fail(self):
        self._test_get_user_home(user_sid=None)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.check_os_version')
    @mock.patch('wmi.WMI')
    def _test_get_network_adapters(self, is_xp_2003, mock_WMI,
                                   mock_check_os_version):
        mock_WMI.return_value = self._conn
        mock_response = mock.MagicMock()
        self._conn.query.return_value = [mock_response]

        mock_check_os_version.return_value = not is_xp_2003

        wql = ('SELECT * FROM Win32_NetworkAdapter WHERE '
               'AdapterTypeId = 0 AND MACAddress IS NOT NULL')

        if not is_xp_2003:
            wql += ' AND PhysicalAdapter = True'

        response = self._winutils.get_network_adapters()
        self._conn.query.assert_called_with(wql)
        self.assertEqual(response, [mock_response.Name])

    def test_get_network_adapters(self):
        self._test_get_network_adapters(False)

    def test_get_network_adapters_xp_2003(self):
        self._test_get_network_adapters(True)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._sanitize_wmi_input')
    def _test_set_static_network_config(self, mock_sanitize_wmi_input,
                                        adapter, ret_val1=None,
                                        ret_val2=None, ret_val3=None):
        wmi.WMI = mock.MagicMock(return_value=self._conn)
        address = '10.10.10.10'
        adapter_name = 'adapter_name'
        broadcast = '0.0.0.0'
        dns_list = ['8.8.8.8']

        if not adapter:
            self.assertRaises(
                Exception, self._winutils.set_static_network_config,
                adapter_name, address, self._NETMASK,
                broadcast, self._GATEWAY, dns_list)
        else:
            mock_sanitize_wmi_input.return_value = adapter_name
            self._conn.query.return_value = adapter
            adapter_config = adapter[0].associators()[0]
            adapter_config.EnableStatic = mock.MagicMock(return_value=ret_val1)
            adapter_config.SetGateways = mock.MagicMock(return_value=ret_val2)
            adapter_config.SetDNSServerSearchOrder = mock.MagicMock(
                return_value=ret_val3)
            adapter.__len__ = mock.MagicMock(return_value=1)
            if ret_val1[0] > 1:
                self.assertRaises(
                    Exception, self._winutils.set_static_network_config,
                    adapter_name, address, self._NETMASK,
                    broadcast, self._GATEWAY, dns_list)

            elif ret_val2[0] > 1:
                self.assertRaises(
                    Exception, self._winutils.set_static_network_config,
                    adapter_name, address, self._NETMASK,
                    broadcast, self._GATEWAY, dns_list)

            elif ret_val3[0] > 1:
                self.assertRaises(
                    Exception, self._winutils.set_static_network_config,
                    adapter_name, address, self._NETMASK,
                    broadcast, self._GATEWAY, dns_list)

            else:
                response = self._winutils.set_static_network_config(
                    adapter_name, address, self._NETMASK,
                    broadcast, self._GATEWAY, dns_list)
                if ret_val1[0] or ret_val2[0] or ret_val3[0] == 1:
                    self.assertTrue(response)
                else:
                    self.assertFalse(response)
                adapter_config.EnableStatic.assert_called_with(
                    [address], [self._NETMASK])
                adapter_config.SetGateways.assert_called_with(
                    [self._GATEWAY], [1])
                adapter_config.SetDNSServerSearchOrder.assert_called_with(
                    dns_list)

                self._winutils._sanitize_wmi_input.assert_called_with(
                    adapter_name)
                adapter[0].associators.assert_called_with(
                    wmi_result_class='Win32_NetworkAdapterConfiguration')
                self._conn.query.assert_called_with(
                    'SELECT * FROM Win32_NetworkAdapter WHERE MACAddress IS '
                    'NOT NULL AND Name = \'%(adapter_name_san)s\'' %
                    {'adapter_name_san': adapter_name})

    def test_set_static_network_config(self):
        adapter = mock.MagicMock()
        ret_val1 = (1,)
        ret_val2 = (1,)
        ret_val3 = (0,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1,
                                             ret_val2=ret_val2,
                                             ret_val3=ret_val3)

    def test_set_static_network_config_query_fail(self):
        self._test_set_static_network_config(adapter=None)

    def test_set_static_network_config_cannot_set_ip(self):
        adapter = mock.MagicMock()
        ret_val1 = (2,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1)

    def test_set_static_network_config_cannot_set_gateway(self):
        adapter = mock.MagicMock()
        ret_val1 = (1,)
        ret_val2 = (2,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1,
                                             ret_val2=ret_val2)

    def test_set_static_network_config_cannot_set_DNS(self):
        adapter = mock.MagicMock()
        ret_val1 = (1,)
        ret_val2 = (1,)
        ret_val3 = (2,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1,
                                             ret_val2=ret_val2,
                                             ret_val3=ret_val3)

    def test_set_static_network_config_no_reboot(self):
        adapter = mock.MagicMock()
        ret_val1 = (0,)
        ret_val2 = (0,)
        ret_val3 = (0,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1,
                                             ret_val2=ret_val2,
                                             ret_val3=ret_val3)

    def _test_get_config_key_name(self, section):
        response = self._winutils._get_config_key_name(section)
        if section:
            self.assertEqual(
                response, self._winutils._config_key + section + '\\')
        else:
            self.assertEqual(response, self._winutils._config_key)

    def test_get_config_key_name_with_section(self):
        self._test_get_config_key_name(self._SECTION)

    def test_get_config_key_name_no_section(self):
        self._test_get_config_key_name(None)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_config_key_name')
    def _test_set_config_value(self, mock_get_config_key_name, value):
        key = mock.MagicMock()
        key_name = self._winutils._config_key + self._SECTION + '\\' + self\
            ._CONFIG_NAME
        mock_get_config_key_name.return_value = key_name

        _winreg.CreateKey = mock.MagicMock()
        _winreg.REG_DWORD = mock.Mock()
        _winreg.REG_SZ = mock.Mock()
        _winreg.SetValueEx = mock.MagicMock()

        self._winutils.set_config_value(self._CONFIG_NAME, value,
                                        self._SECTION)

        _winreg.CreateKey.__enter__.return_value = key
        with _winreg.CreateKey as m:
            assert m == key

        _winreg.CreateKey.__enter__.assert_called_with()
        _winreg.CreateKey.__exit__.assert_called_with(None, None, None)
        _winreg.CreateKey.assert_called_with(_winreg.HKEY_LOCAL_MACHINE,
                                             key_name)
        mock_get_config_key_name.assert_called_with(self._SECTION)
        if type(value) == int:
            _winreg.SetValueEx.assert_called_with(
                _winreg.CreateKey().__enter__(), self._CONFIG_NAME, 0,
                _winreg.REG_DWORD, value)
        else:
            _winreg.SetValueEx.assert_called_with(
                _winreg.CreateKey().__enter__(), self._CONFIG_NAME, 0,
                _winreg.REG_SZ, value)

    def test_set_config_value_int(self):
        self._test_set_config_value(value=1)

    def test_set_config_value_not_int(self):
        self._test_set_config_value(value='1')

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_config_key_name')
    def _test_get_config_value(self, mock_get_config_key_name, value):
        key_name = self._winutils._config_key + self._SECTION + '\\'
        key_name += self._CONFIG_NAME
        _winreg.OpenKey = mock.MagicMock()
        _winreg.REG_DWORD = mock.Mock()
        _winreg.REG_SZ = mock.Mock()
        if type(value) == int:
            regtype = _winreg.REG_DWORD
        else:
            regtype = _winreg.REG_SZ
        _winreg.QueryValueEx = mock.MagicMock(return_value=(value, regtype))
        if value is None:
            mock_get_config_key_name.side_effect = [WindowsError]
            self.assertRaises(WindowsError, self._winutils.get_config_value,
                              self._CONFIG_NAME, None)
        else:
            mock_get_config_key_name.return_value = key_name
            response = self._winutils.get_config_value(self._CONFIG_NAME,
                                                       self._SECTION)
            _winreg.OpenKey.assert_called_with(_winreg.HKEY_LOCAL_MACHINE,
                                               key_name)
            mock_get_config_key_name.assert_called_with(self._SECTION)
            _winreg.QueryValueEx.assert_called_with(
                _winreg.OpenKey().__enter__(), self._CONFIG_NAME)
            self.assertEqual(response, value)

    def test_get_config_value_type_int(self):
        self._test_get_config_value(value=1)

    def test_get_config_value_type_str(self):
        self._test_get_config_value(value='fake')

    def test_get_config_value_type_error(self):
        self._test_get_config_value(value=None)

    def _test_wait_for_boot_completion(self, ret_val):
        key = mock.MagicMock()
        time.sleep = mock.MagicMock()
        _winreg.OpenKey = mock.MagicMock()
        _winreg.QueryValueEx = mock.MagicMock()
        _winreg.QueryValueEx.side_effect = ret_val
        self._winutils.wait_for_boot_completion()
        _winreg.OpenKey.__enter__.return_value = key
        _winreg.OpenKey.assert_called_with(
            _winreg.HKEY_LOCAL_MACHINE,
            "SYSTEM\\Setup\\Status\\SysprepStatus", 0, _winreg.KEY_READ)

        _winreg.QueryValueEx.assert_called_with(
            _winreg.OpenKey().__enter__(), "GeneralizationState")

    def test_wait_for_boot_completion(self):
        ret_val = [[7]]
        self._test_wait_for_boot_completion(ret_val)

    @mock.patch('wmi.WMI')
    def test_get_service(self, mock_WMI):
        mock_WMI.return_value = self._conn
        self._conn.Win32_Service.return_value = ['fake name']
        response = self._winutils._get_service('fake name')
        mock_WMI.assert_called_with(moniker='//./root/cimv2')
        self._conn.Win32_Service.assert_called_with(Name='fake name')
        self.assertEqual(response, 'fake name')

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def test_check_service_exists(self, mock_get_service):
        mock_get_service.return_value = 'not None'
        response = self._winutils.check_service_exists('fake name')
        self.assertEqual(response, True)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def test_get_service_status(self, mock_get_service):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        response = self._winutils.get_service_status('fake name')
        self.assertEqual(response, mock_service.State)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def test_get_service_start_mode(self, mock_get_service):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        response = self._winutils.get_service_start_mode('fake name')
        self.assertEqual(response, mock_service.StartMode)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def _test_set_service_start_mode(self, mock_get_service, ret_val):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.ChangeStartMode.return_value = (ret_val,)
        if ret_val != 0:
            self.assertRaises(Exception,
                              self._winutils.set_service_start_mode,
                              'fake name', 'fake mode')
        else:
            self._winutils.set_service_start_mode('fake name', 'fake mode')
        mock_service.ChangeStartMode.assert_called_once_with('fake mode')

    def test_set_service_start_mode(self):
        self._test_set_service_start_mode(ret_val=0)

    def test_set_service_start_mode_exception(self):
        self._test_set_service_start_mode(ret_val=1)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def _test_start_service(self, mock_get_service, ret_val):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.StartService.return_value = (ret_val,)
        if ret_val != 0:
            self.assertRaises(Exception,
                              self._winutils.start_service,
                              'fake name')
        else:
            self._winutils.start_service('fake name')
        mock_service.StartService.assert_called_once_with()

    def test_start_service(self):
        self._test_set_service_start_mode(ret_val=0)

    def test_start_service_exception(self):
        self._test_set_service_start_mode(ret_val=1)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def _test_stop_service(self, mock_get_service, ret_val):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.StopService.return_value = (ret_val,)
        if ret_val != 0:
            self.assertRaises(Exception,
                              self._winutils.stop_service,
                              'fake name')
        else:
            self._winutils.stop_service('fake name')
        mock_service.StopService.assert_called_once_with()

    def test_stop_service(self):
        self._test_stop_service(ret_val=0)

    def test_stop_service_exception(self):
        self._test_stop_service(ret_val=1)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.stop_service')
    def test_terminate(self, mock_stop_service):
        time.sleep = mock.MagicMock()
        self._winutils.terminate()
        mock_stop_service.assert_called_with(self._winutils._service_name)
        time.sleep.assert_called_with(3)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_ipv4_routing_table')
    def _test_get_default_gateway(self, mock_get_ipv4_routing_table,
                                  routing_table):
        mock_get_ipv4_routing_table.return_value = [routing_table]
        response = self._winutils.get_default_gateway()
        mock_get_ipv4_routing_table.assert_called_once_with()
        if routing_table[0] == '0.0.0.0':
            self.assertEqual(response, (routing_table[3], routing_table[2]))
        else:
            self.assertEqual(response, (None, None))

    def test_get_default_gateway(self):
        routing_table = ['0.0.0.0', '1.1.1.1', self._GATEWAY, '8.8.8.8']
        self._test_get_default_gateway(routing_table=routing_table)

    def test_get_default_gateway_error(self):
        routing_table = ['1.1.1.1', '1.1.1.1', self._GATEWAY, '8.8.8.8']
        self._test_get_default_gateway(routing_table=routing_table)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_ipv4_routing_table')
    def _test_check_static_route_exists(self, mock_get_ipv4_routing_table,
                                        routing_table):
        mock_get_ipv4_routing_table.return_value = [routing_table]
        response = self._winutils.check_static_route_exists(self._DESTINATION)
        mock_get_ipv4_routing_table.assert_called_once_with()
        if routing_table[0] == self._DESTINATION:
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_check_static_route_exists_true(self):
        routing_table = [self._DESTINATION, '1.1.1.1', self._GATEWAY,
                         '8.8.8.8']
        self._test_check_static_route_exists(routing_table=routing_table)

    def test_check_static_route_exists_false(self):
        routing_table = ['0.0.0.0', '1.1.1.1', self._GATEWAY, '8.8.8.8']
        self._test_check_static_route_exists(routing_table=routing_table)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.execute_process')
    def _test_add_static_route(self, mock_execute_process, err):
        next_hop = '10.10.10.10'
        interface_index = 1
        metric = 9
        args = ['ROUTE', 'ADD', self._DESTINATION, 'MASK', self._NETMASK,
                next_hop]
        mock_execute_process.return_value = (None, err, None)
        if err:
            self.assertRaises(Exception, self._winutils.add_static_route,
                              self._DESTINATION, self._NETMASK, next_hop,
                              interface_index, metric)
        else:
            self._winutils.add_static_route(self._DESTINATION, self._NETMASK,
                                            next_hop, interface_index, metric)
            mock_execute_process.assert_called_with(args)

    def test_add_static_route(self):
        self._test_add_static_route(err=404)

    def test_add_static_route_fail(self):
        self._test_add_static_route(err=None)

    @mock.patch('ctypes.sizeof')
    @mock.patch('ctypes.byref')
    @mock.patch('ctypes.windll.kernel32.VerSetConditionMask')
    @mock.patch('ctypes.windll.kernel32.VerifyVersionInfoW')
    @mock.patch('ctypes.windll.kernel32.GetLastError')
    def _test_check_os_version(self, mock_GetLastError,
                               mock_VerifyVersionInfoW,
                               mock_VerSetConditionMask, mock_byref,
                               mock_sizeof, ret_value, error_value=None):
        mock_VerSetConditionMask.return_value = 2
        mock_VerifyVersionInfoW.return_value = ret_value
        mock_GetLastError.return_value = error_value
        old_version = self._winutils.ERROR_OLD_WIN_VERSION
        if error_value and error_value is not old_version:
            self.assertRaises(Exception, self._winutils.check_os_version, 3,
                              1, 2)
            mock_GetLastError.assert_called_once_with()
        else:
            response = self._winutils.check_os_version(3, 1, 2)
            mock_sizeof.assert_called_once_with(
                windows_utils.Win32_OSVERSIONINFOEX_W)
            self.assertEqual(mock_VerSetConditionMask.call_count, 3)
            mock_VerifyVersionInfoW.assert_called_with(mock_byref(),
                                                       1 | 2 | 3 | 7,
                                                       2)
            if error_value is old_version:
                mock_GetLastError.assert_called_with()
                self.assertEqual(response, False)
            else:
                self.assertEqual(response, True)

    def test_check_os_version(self):
        m = mock.MagicMock()
        self._test_check_os_version(ret_value=m)

    def test_check_os_version_expect_False(self):
        self._test_check_os_version(
            ret_value=None, error_value=self._winutils.ERROR_OLD_WIN_VERSION)

    def test_check_os_version_exception(self):
        self._test_check_os_version(ret_value=None, error_value=9999)

    def _test_get_volume_label(self, ret_val):
        label = mock.MagicMock()
        max_label_size = 261
        drive = 'Fake_drive'
        ctypes.create_unicode_buffer = mock.MagicMock(return_value=label)
        ctypes.windll.kernel32.GetVolumeInformationW = mock.MagicMock(
            return_value=ret_val)
        response = self._winutils.get_volume_label(drive)
        if ret_val:
            self.assertTrue(response is not None)
        else:
            self.assertTrue(response is None)

        ctypes.create_unicode_buffer.assert_called_with(max_label_size)
        ctypes.windll.kernel32.GetVolumeInformationW.assert_called_with(
            drive, label, max_label_size, 0, 0, 0, 0, 0)

    def test_get_volume_label(self):
        self._test_get_volume_label('ret')

    def test_get_volume_label_no_return_value(self):
        self._test_get_volume_label(None)

    @mock.patch('re.search')
    @mock.patch('cloudbaseinit.osutils.base.BaseOSUtils.'
                'generate_random_password')
    def test_generate_random_password(self, mock_generate_random_password,
                                      mock_search):
        length = 14
        mock_search.return_value = True
        mock_generate_random_password.return_value = 'Passw0rd'
        response = self._winutils.generate_random_password(length)
        mock_generate_random_password.assert_called_once_with(length)
        self.assertEqual(response, 'Passw0rd')

    @mock.patch('ctypes.create_unicode_buffer')
    @mock.patch('ctypes.windll.kernel32.GetLogicalDriveStringsW')
    def _test_get_logical_drives(self, mock_GetLogicalDriveStringsW,
                                 mock_create_unicode_buffer, buf_length):
        mock_buf = mock.MagicMock()
        mock_buf.__getitem__.side_effect = ['1', '\x00']
        mock_create_unicode_buffer.return_value = mock_buf
        mock_GetLogicalDriveStringsW.return_value = buf_length
        if buf_length is None:
            self.assertRaises(Exception, self._winutils._get_logical_drives)
        else:
            response = self._winutils._get_logical_drives()
            print mock_buf.mock_calls
            mock_create_unicode_buffer.assert_called_with(261)
            mock_GetLogicalDriveStringsW.assert_called_with(260, mock_buf)
            self.assertEqual(response, ['1'])

    def test_get_logical_drives_exception(self):
        self._test_get_logical_drives(buf_length=None)

    def test_get_logical_drives(self):
        self._test_get_logical_drives(buf_length=2)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils.'
                '_get_logical_drives')
    @mock.patch('cloudbaseinit.osutils.windows.kernel32')
    def test_get_cdrom_drives(self, mock_kernel32, mock_get_logical_drives):
        mock_get_logical_drives.return_value = ['drive']
        mock_kernel32.GetDriveTypeW.return_value = self._winutils.DRIVE_CDROM
        response = self._winutils.get_cdrom_drives()
        mock_get_logical_drives.assert_called_with()
        self.assertEqual(response, ['drive'])

    @mock.patch('cloudbaseinit.osutils.windows.msvcrt')
    @mock.patch('cloudbaseinit.osutils.windows.kernel32')
    @mock.patch('cloudbaseinit.osutils.windows.setupapi')
    @mock.patch('cloudbaseinit.osutils.windows.Win32_STORAGE_DEVICE_NUMBER')
    @mock.patch('ctypes.byref')
    @mock.patch('ctypes.sizeof')
    @mock.patch('ctypes.wintypes.DWORD')
    @mock.patch('ctypes.cast')
    @mock.patch('ctypes.POINTER')
    def _test_get_physical_disks(self, mock_POINTER, mock_cast,
                                 mock_DWORD, mock_sizeof, mock_byref,
                                 mock_sdn, mock_setupapi, mock_kernel32,
                                 mock_msvcrt, handle_disks, last_error,
                                 interface_detail, disk_handle, io_control):

        sizeof_calls = [mock.call(
            windows_utils.Win32_SP_DEVICE_INTERFACE_DATA),
            mock.call(mock_sdn())]
        device_interfaces_calls = [mock.call(handle_disks, None, mock_byref(),
                                             0, mock_byref()),
                                   mock.call(handle_disks, None, mock_byref(),
                                             1, mock_byref())]
        cast_calls = [mock.call(),
                      mock.call(mock_msvcrt.malloc(), mock_POINTER()),
                      mock.call(mock_cast().contents.DevicePath,
                                wintypes.LPWSTR)]

        mock_setup_interface = mock_setupapi.SetupDiGetDeviceInterfaceDetailW

        mock_setupapi.SetupDiGetClassDevsW.return_value = handle_disks
        mock_kernel32.GetLastError.return_value = last_error
        mock_setup_interface.return_value = interface_detail
        mock_kernel32.CreateFileW.return_value = disk_handle
        mock_kernel32.DeviceIoControl.return_value = io_control

        mock_setupapi.SetupDiEnumDeviceInterfaces.side_effect = [True, False]

        if handle_disks == self._winutils.INVALID_HANDLE_VALUE or (
            last_error != self._winutils.ERROR_INSUFFICIENT_BUFFER) and not (
                interface_detail) or (
                    disk_handle == self._winutils.INVALID_HANDLE_VALUE) or (
                        not io_control):

            self.assertRaises(Exception, self._winutils.get_physical_disks)

        else:
            response = self._winutils.get_physical_disks()
            self.assertEqual(mock_sizeof.call_args_list, sizeof_calls)
            self.assertEqual(
                mock_setupapi.SetupDiEnumDeviceInterfaces.call_args_list,
                device_interfaces_calls)
            if not interface_detail:
                mock_kernel32.GetLastError.assert_called_once_with()

            mock_POINTER.assert_called_with(
                windows_utils.Win32_SP_DEVICE_INTERFACE_DETAIL_DATA_W)
            mock_msvcrt.malloc.assert_called_with(mock_DWORD())

            self.assertEqual(mock_cast.call_args_list, cast_calls)

            mock_setup_interface.assert_called_with(handle_disks, mock_byref(),
                                                    mock_cast(), mock_DWORD(),
                                                    None, None)
            mock_kernel32.CreateFileW.assert_called_with(
                mock_cast().value, 0, self._winutils.FILE_SHARE_READ, None,
                self._winutils.OPEN_EXISTING, 0, 0)
            mock_sdn.assert_called_with()

            mock_kernel32.DeviceIoControl.assert_called_with(
                disk_handle, self._winutils.IOCTL_STORAGE_GET_DEVICE_NUMBER,
                None, 0, mock_byref(), mock_sizeof(), mock_byref(), None)
            self.assertEqual(response, ["\\\\.\PHYSICALDRIVE1"])
            mock_setupapi.SetupDiDestroyDeviceInfoList.assert_called_once_with(
                handle_disks)

        mock_setupapi.SetupDiGetClassDevsW.assert_called_once_with(
            mock_byref(), None, None, self._winutils.DIGCF_PRESENT |
            self._winutils.DIGCF_DEVICEINTERFACE)

    def test_get_physical_disks(self):
        mock_handle_disks = mock.MagicMock()
        mock_disk_handle = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=mock_handle_disks,
            last_error=self._winutils.ERROR_INSUFFICIENT_BUFFER,
            interface_detail='fake interface detail',
            disk_handle=mock_disk_handle, io_control=True)

    def test_get_physical_disks_other_error_and_no_interface_detail(self):
        mock_handle_disks = mock.MagicMock()
        mock_disk_handle = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=mock_handle_disks,
            last_error='other', interface_detail=None,
            disk_handle=mock_disk_handle, io_control=True)

    def test_get_physical_disks_invalid_disk_handle(self):
        mock_handle_disks = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=mock_handle_disks,
            last_error=self._winutils.ERROR_INSUFFICIENT_BUFFER,
            interface_detail='fake interface detail',
            disk_handle=self._winutils.INVALID_HANDLE_VALUE, io_control=True)

    def test_get_physical_disks_io_control(self):
        mock_handle_disks = mock.MagicMock()
        mock_disk_handle = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=mock_handle_disks,
            last_error=self._winutils.ERROR_INSUFFICIENT_BUFFER,
            interface_detail='fake interface detail',
            disk_handle=mock_disk_handle, io_control=False)

    def test_get_physical_disks_handle_disks_invalid(self):
        mock_disk_handle = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=self._winutils.INVALID_HANDLE_VALUE,
            last_error=self._winutils.ERROR_INSUFFICIENT_BUFFER,
            interface_detail='fake interface detail',
            disk_handle=mock_disk_handle, io_control=True)

    @mock.patch('win32com.client.Dispatch')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils._get_fw_protocol')
    def _test_firewall_create_rule(self, mock_get_fw_protocol, mock_Dispatch):
        self._winutils.firewall_create_rule(
            name='fake name', port=9999, protocol=self._winutils.PROTOCOL_TCP)
        expected = [mock.call("HNetCfg.FWOpenPort"),
                    mock.call("HNetCfg.FwMgr")]
        self.assertEqual(mock_Dispatch.call_args_list, expected)
        mock_get_fw_protocol.assert_called_once_with(
            self._winutils.PROTOCOL_TCP)

    @mock.patch('win32com.client.Dispatch')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils._get_fw_protocol')
    def test_firewall_remove_rule(self, mock_get_fw_protocol, mock_Dispatch):
        self._winutils.firewall_remove_rule(
            name='fake name', port=9999, protocol=self._winutils.PROTOCOL_TCP)
        mock_Dispatch.assert_called_once_with("HNetCfg.FwMgr")
        mock_get_fw_protocol.assert_called_once_with(
            self._winutils.PROTOCOL_TCP)

    @mock.patch('ctypes.wintypes.BOOL')
    @mock.patch('cloudbaseinit.osutils.windows.kernel32.IsWow64Process')
    @mock.patch('cloudbaseinit.osutils.windows.kernel32.GetCurrentProcess')
    @mock.patch('ctypes.byref')
    def _test_is_wow64(self, mock_byref, mock_GetCurrentProcess,
                       mock_IsWow64Process, mock_BOOL, ret_val):
        mock_IsWow64Process.return_value = ret_val
        mock_BOOL().value = ret_val
        if ret_val is False:
            self.assertRaises(Exception, self._winutils.is_wow64)
        else:
            response = self._winutils.is_wow64()
            mock_byref.assert_called_once_with(mock_BOOL())
            mock_IsWow64Process.assert_called_once_with(
                mock_GetCurrentProcess(), mock_byref())
            self.assertEqual(response, True)

    def test_is_wow64(self):
        self._test_is_wow64(ret_val=True)

    def test_is_wow64_exception(self):
        self._test_is_wow64(ret_val=False)

    @mock.patch('os.path.expandvars')
    def test_get_system32_dir(self, mock_expandvars):
        mock_expandvars.return_value = 'fake_system32'
        response = self._winutils.get_system32_dir()
        self.assertEqual(response, 'fake_system32')

    @mock.patch('os.path.expandvars')
    def test_get_sysnative_dir(self, mock_expandvars):
        mock_expandvars.return_value = 'fake_sysnative'
        response = self._winutils.get_sysnative_dir()
        self.assertEqual(response, 'fake_sysnative')

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_sysnative_dir')
    @mock.patch('os.path.isdir')
    def test_check_sysnative_dir_exists(self, mock_isdir,
                                        mock_get_sysnative_dir):
        mock_get_sysnative_dir.return_value = 'fake_sysnative'
        mock_isdir.return_value = True
        response = self._winutils.check_sysnative_dir_exists()
        self.assertEqual(response, True)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.check_sysnative_dir_exists')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_sysnative_dir')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_system32_dir')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.execute_process')
    def _test_execute_powershell_script(self, mock_execute_process,
                                        mock_get_system32_dir,
                                        mock_get_sysnative_dir,
                                        mock_check_sysnative_dir_exists,
                                        ret_val):
        mock_check_sysnative_dir_exists.return_value = ret_val
        mock_get_sysnative_dir.return_value = 'fake'
        mock_get_system32_dir.return_value = 'fake'
        fake_path = os.path.join('fake', 'WindowsPowerShell\\v1.0\\'
                                         'powershell.exe')
        args = [fake_path, '-ExecutionPolicy', 'RemoteSigned',
                '-NonInteractive', '-File', 'fake_script_path']
        response = self._winutils.execute_powershell_script(
            script_path='fake_script_path')
        if ret_val is True:
            mock_get_sysnative_dir.assert_called_once_with()
        else:
            mock_get_system32_dir.assert_called_once_with()
        mock_execute_process.assert_called_with(args, False)
        self.assertEqual(response, mock_execute_process())

    def test_execute_powershell_script_sysnative(self):
        self._test_execute_powershell_script(ret_val=True)

    def test_execute_powershell_script_system32(self):
        self._test_execute_powershell_script(ret_val=False)

    @mock.patch('cloudbaseinit.utils.windows.network.get_adapter_addresses')
    def test_get_dhcp_hosts_in_use(self, mock_get_adapter_addresses):
        net_addr = {}
        net_addr["mac_address"] = 'fake mac address'
        net_addr["dhcp_server"] = 'fake dhcp server'
        net_addr["dhcp_enabled"] = True
        mock_get_adapter_addresses.return_value = [net_addr]
        response = self._winutils.get_dhcp_hosts_in_use()
        mock_get_adapter_addresses.assert_called()
        self.assertEqual(response, [('fake mac address', 'fake dhcp server')])

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.check_sysnative_dir_exists')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_sysnative_dir')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_system32_dir')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.execute_process')
    def _test_set_ntp_client_config(self, mock_execute_process,
                                    mock_get_system32_dir,
                                    mock_get_sysnative_dir,
                                    mock_check_sysnative_dir_exists,
                                    sysnative, ret_val):
        mock_check_sysnative_dir_exists.return_value = sysnative
        fake_base_dir = 'fake_dir'
        mock_execute_process.return_value = (None, None, ret_val)
        w32tm_path = os.path.join(fake_base_dir, "w32tm.exe")
        mock_get_sysnative_dir.return_value = fake_base_dir
        mock_get_system32_dir.return_value = fake_base_dir
        args = [w32tm_path, '/config', '/manualpeerlist:%s' % 'fake ntp host',
                '/syncfromflags:manual', '/update']

        if ret_val:
            self.assertRaises(Exception, self._winutils.set_ntp_client_config,
                              args, False)
        else:
            self._winutils.set_ntp_client_config(ntp_host='fake ntp host')

            if sysnative:
                mock_get_sysnative_dir.assert_called_once_with()
            else:
                mock_get_system32_dir.assert_called_once_with()
            mock_execute_process.assert_called_once_with(args, False)

    def test_set_ntp_client_config_sysnative_true(self):
        self._test_set_ntp_client_config(sysnative=True, ret_val=None)

    def test_set_ntp_client_config_sysnative_false(self):
        self._test_set_ntp_client_config(sysnative=False, ret_val=None)

    def test_set_ntp_client_config_sysnative_exception(self):
        self._test_set_ntp_client_config(sysnative=False,
                                         ret_val='fake return value')
