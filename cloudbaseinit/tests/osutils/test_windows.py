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

import _winreg
import ctypes
import mock
import time
import unittest
import win32process
import win32security
import wmi

from ctypes import windll
from ctypes import wintypes

from cloudbaseinit.openstack.common import cfg
from cloudbaseinit.osutils import windows as windows_utils

CONF = cfg.CONF


class WindowsUtilsTest(unittest.TestCase):
    '''Tests for the windows utils class'''

    _CONFIG_NAME = 'FakeConfig'
    _DESTINATION = 'Fake/destination'
    _GATEWAY = '10.7.1.1'
    _NETMASK = '255.255.255.0'
    _PASSWORD = 'Passw0rd'
    _SECTION = 'fake_section'
    _SERVICE_NAME = 'cloudbase-init'
    _USERNAME = 'Admin'

    def setUp(self):
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

    def _test_reboot(self, ret_value):
        self._winutils._enable_shutdown_privilege = mock.MagicMock()

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
        self._test_reboot(True)

    def test_reboot_failed(self):
        self._test_reboot(None)

    def _test_get_user_wmi_object(self, returnvalue):
        wmi.WMI = mock.MagicMock(return_value=self._conn)

        self._winutils._sanitize_wmi_input = mock.MagicMock(
            return_value=self._USERNAME)

        self._conn.query = mock.MagicMock(return_value=returnvalue)

        response = self._winutils._get_user_wmi_object(self._USERNAME)

        self._conn.query.assert_called_with("SELECT * FROM Win32_Account "
                                            "where name = \'%s\'" %
                                            self._USERNAME)
        self._winutils._sanitize_wmi_input.assert_called_with(self._USERNAME)
        wmi.WMI.assert_called_with(moniker='//./root/cimv2')

        if returnvalue:
            self.assertIsNotNone(response)
        else:
            self.assertIsNone(response)

    def test_get_user_wmi_object(self):
        caption = 'fake'
        self._test_get_user_wmi_object(caption)

    def test_no_user_wmi_object(self):
        empty_caption = ''
        self._test_get_user_wmi_object(empty_caption)

    def _test_user_exists(self, returnvalue):
        self._winutils._get_user_wmi_object = mock.MagicMock(
            return_value=returnvalue)
        response = self._winutils.user_exists(returnvalue)
        if returnvalue:
            self._winutils._get_user_wmi_object.assert_called_with(returnvalue)
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_user_exists(self):
        self._test_user_exists(self._USERNAME)

    def test_username_does_not_exist(self):
        self._test_user_exists(None)

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

    def _test_create_or_change_user(self, create, password_expires,
                                    ret_value=0):

        side_effect = lambda value: value
        self._winutils.sanitize_shell_input = mock.MagicMock(
            side_effect=side_effect)

        args = ['NET', 'USER', self._USERNAME, self._PASSWORD]
        if create:
            args.append('/ADD')

        self._winutils.execute_process = mock.MagicMock(
            return_value=(None, None, ret_value))
        if not ret_value:
            self._winutils._set_user_password_expiration = mock.MagicMock()
            self._winutils._create_or_change_user(self._USERNAME,
                                                  self._PASSWORD, create,
                                                  password_expires)

            assert self._winutils.sanitize_shell_input.call_count == 2
            self._winutils._set_user_password_expiration.assert_called_with(
                self._USERNAME, password_expires)
        else:
            self.assertRaises(
                Exception, self._winutils._create_or_change_user,
                self._USERNAME, self._PASSWORD, create, password_expires)

        self._winutils.execute_process.assert_called_with(args)

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

    def _test_set_user_password_expiration(self, fake_obj):
        self._winutils._get_user_wmi_object = mock.MagicMock(
            return_value=fake_obj)

        response = self._winutils._set_user_password_expiration(
            self._USERNAME,
            True)
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

    def _test_get_user_sid_and_domain(self, ret_val):

        cbSid = mock.Mock()
        sid = mock.Mock()
        size = 1024
        cchReferencedDomainName = mock.Mock()
        domainName = mock.Mock()
        sidNameUse = mock.Mock()

        #VERIFY multiple calls, multiple return values, same method
        ctypes.create_string_buffer = mock.MagicMock(return_value=sid)
        ctypes.sizeof = mock.MagicMock(return_value=size)
        wintypes.DWORD = mock.MagicMock(return_value=cbSid)
        # wintypes.DWORD.return_value=cbSid
        ctypes.create_unicode_buffer = mock.MagicMock(return_value=domainName)
        wintypes.DWORD.return_value = cchReferencedDomainName

        ctypes.byref = mock.MagicMock()

        windll.advapi32.LookupAccountNameW = mock.MagicMock(
            return_value=ret_val)
        if ret_val is None:
            self.assertRaises(
                Exception, self._winutils._get_user_sid_and_domain,
                self._USERNAME)
        else:
            response = self._winutils._get_user_sid_and_domain(self._USERNAME)

            windll.advapi32.LookupAccountNameW.assert_called_with(
                0, unicode(self._USERNAME), sid, ctypes.byref(cbSid),
                domainName, ctypes.byref(cchReferencedDomainName),
                ctypes.byref(sidNameUse))
            self.assertEqual(response, (sid, domainName.value))

    def test_get_user_sid_and_domain(self):
        fake_obj = mock.Mock()
        self._test_get_user_sid_and_domain(fake_obj)

    def test_get_user_sid_and_domain_no_return_value(self):
        self._test_get_user_sid_and_domain(None)

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

    def _test_get_user_sid(self, fail=False):
        r = mock.Mock()

        if not fail:
            self._winutils._get_user_wmi_object = mock.MagicMock(
                return_value=None)
            response = self._winutils.get_user_sid(self._USERNAME)
            self.assertIsNone(response)
        else:
            self._winutils._get_user_wmi_object = mock.MagicMock(
                return_value=r)
            response = self._winutils.get_user_sid(self._USERNAME)
            self.assertIsNotNone(response)

        self._winutils._get_user_wmi_object.assert_called_with(self._USERNAME)

    def test_get_user_sid(self):
        self._test_get_user_sid()

    def test_get_user_sid_fail(self):
        self._test_get_user_sid(True)

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
            windll.userenv.LoadUserProfileW = mock.MagicMock(return_value=None)
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
            self.assertIsNotNone(response)
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
            self.assertIsNotNone(response)

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

    def _test_set_host_name(self, new_host_name, comp_name):
        wmi.WMI = mock.MagicMock(return_value=self._conn)

        comp = self._conn.Win32_ComputerSystem()[0]
        comp.Name = comp_name
        response = self._winutils.set_host_name(new_host_name)

        if new_host_name is not comp_name:
            comp.Rename.assert_called_with(new_host_name, None, None)
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_set_host_name(self):
        self._test_set_host_name('fake', 'fake2')

    def test_set_host_name_same_name(self):
        host_name = 'fake'
        self._test_set_host_name(host_name, host_name)

    def _test_get_user_home(self, user_sid):
        key = mock.MagicMock()
        self._winutils.get_user_sid = mock.MagicMock(return_value=user_sid)

        if user_sid:
            _winreg.OpenKey = mock.MagicMock(return_value=key)
            _winreg.QueryValueEx = mock.MagicMock()

            response = self._winutils.get_user_home(self._USERNAME)

            _winreg.OpenKey.__enter__ = mock.MagicMock(return_value=key)
            _winreg.OpenKey.__exit__ = mock.MagicMock(return_value=False)
            with _winreg.OpenKey as m:
                assert m == key

            _winreg.OpenKey.__enter__.assert_called_with()
            _winreg.OpenKey.__exit__.assert_called_with(None, None, None)
            _winreg.OpenKey.assert_called_with(
                _winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows '
                                            'NT\\CurrentVersion\\ProfileList\\'
                                            '%s' % user_sid)
            self.assertIsNotNone(response)
            _winreg.QueryValueEx.assert_called_with(
                _winreg.OpenKey().__enter__(), 'ProfileImagePath')
        else:
            response = self._winutils.get_user_home(self._USERNAME)
            self.assertIsNone(response)
        self._winutils.get_user_sid.assert_called_with(self._USERNAME)

    def test_get_user_home(self):
        user = mock.MagicMock()
        self._test_get_user_home(user)

    def test_get_user_home_fail(self):
        self._test_get_user_home(None)

    def test_get_network_adapters(self):
        wmi.WMI = mock.MagicMock(return_value=self._conn)
        response = self._winutils.get_network_adapters()
        self._conn.query.assert_called_with(
            'SELECT * FROM Win32_NetworkAdapter WHERE AdapterTypeId = 0 AND '
            'PhysicalAdapter = True AND MACAddress IS NOT NULL')
        self.assertIsNotNone(response)

    def _test_set_static_network_config(self, adapter, ret_val1=None,
                                        ret_val2=None,
                                        ret_val3=None):
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
            self._winutils._sanitize_wmi_input = mock.MagicMock(
                return_value=adapter_name)
            self._conn.query.return_value = adapter

            adapter_config = adapter[0].associators()[0]
            adapter_config.EnableStatic = mock.MagicMock(return_value=ret_val1)
            adapter_config.SetGateways = mock.MagicMock(return_value=ret_val2)
            adapter_config.SetDNSServerSearchOrder = mock.MagicMock(
                return_value=ret_val3)
            adapter.__len__ = mock.MagicMock(return_value=1)
            print ret_val1[0]
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
        self._test_set_static_network_config(adapter, ret_val1, ret_val2,
                                             ret_val3)

    def test_set_static_network_config_query_fail(self):
        adapter = None
        self._test_set_static_network_config(adapter)

    def test_set_static_network_config_cannot_set_ip(self):
        adapter = mock.MagicMock()
        ret_val1 = (2,)
        self._test_set_static_network_config(adapter, ret_val1)

    def test_set_static_network_config_cannot_set_gateway(self):
        adapter = mock.MagicMock()
        ret_val1 = (1,)
        ret_val2 = (2,)
        self._test_set_static_network_config(adapter, ret_val1, ret_val2)

    def test_set_static_network_config_cannot_set_DNS(self):
        adapter = mock.MagicMock()
        ret_val1 = (1,)
        ret_val2 = (1,)
        ret_val3 = (2,)
        self._test_set_static_network_config(adapter, ret_val1, ret_val2,
                                             ret_val3)

    def test_set_static_network_config_no_reboot(self):
        adapter = mock.MagicMock()
        ret_val1 = (0,)
        ret_val2 = (0,)
        ret_val3 = (0,)
        self._test_set_static_network_config(adapter, ret_val1, ret_val2,
                                             ret_val3)

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

    def _test_set_config_value(self, value):
        key = mock.MagicMock()
        key_name = self._winutils._config_key + self._SECTION + '\\' + self\
            ._CONFIG_NAME
        self._winutils._get_config_key_name = mock.MagicMock(
            return_value=key_name)

        _winreg.CreateKey = mock.MagicMock()
        _winreg.REG_DWORD = mock.Mock()
        _winreg.REG_SZ = mock.Mock()
        _winreg.SetValueEx = mock.MagicMock()

        self._winutils.set_config_value(self._CONFIG_NAME, value,
                                        self._SECTION)

        _winreg.CreateKey.__enter__ = mock.MagicMock(return_value=key)
        _winreg.CreateKey.__exit__ = mock.MagicMock()
        with _winreg.CreateKey as m:
            assert m == key

        _winreg.CreateKey.__enter__.assert_called_with()
        _winreg.CreateKey.__exit__.assert_called_with(None, None, None)
        _winreg.CreateKey.assert_called_with(_winreg.HKEY_LOCAL_MACHINE,
                                             key_name)
        self._winutils._get_config_key_name.assert_called_with(self._SECTION)
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

    def _test_get_config_value(self, value):
        if not value:
            self.assertRaises(WindowsError, self._winutils.set_config_value,
                              self._CONFIG_NAME, self._SECTION)
        else:
            key = mock.MagicMock()
            key_name = self._winutils._config_key + self._SECTION + \
                '\\' + self._CONFIG_NAME
            self._winutils._get_config_key_name = mock.MagicMock(
                return_value=key_name)

            _winreg.OpenKey = mock.MagicMock()
            _winreg.REG_DWORD = mock.Mock()
            _winreg.REG_SZ = mock.Mock()
            if type(value) == int:
                regtype = _winreg.REG_DWORD
            else:
                regtype = _winreg.REG_SZ
            _winreg.QueryValueEx = mock.MagicMock(
                return_value=(value, regtype))

            response = self._winutils.get_config_value(self._CONFIG_NAME,
                                                       self._SECTION)

            _winreg.OpenKey.__enter__ = mock.MagicMock(return_value=key)
            _winreg.OpenKey.__exit__ = mock.MagicMock()
            with _winreg.OpenKey as m:
                assert m == key

            _winreg.OpenKey.__enter__.assert_called_with()
            _winreg.OpenKey.__exit__.assert_called_with(None, None, None)
            _winreg.OpenKey.assert_called_with(_winreg.HKEY_LOCAL_MACHINE,
                                               key_name)

            self._winutils._get_config_key_name.assert_called_with(
                self._SECTION)
            _winreg.QueryValueEx.assert_called_with(
                _winreg.OpenKey().__enter__(), self._CONFIG_NAME)
            self.assertIsNotNone(response)

    def test_get_config_value_type_int(self):
        self._test_get_config_value(1)

    def test_get_config_value_type_str(self):
        self._test_get_config_value('fake')

    def test_get_config_value_type_error(self):
        self._test_get_config_value(None)

    def _test_delete_config_value(self, key):
        _winreg.OpenKey = mock.MagicMock()
        _winreg.DeleteKey = mock.MagicMock()

        response = self._winutils.delete_config_value(self._SECTION)

        _winreg.OpenKey.__enter__ = mock.MagicMock(return_value=key)
        _winreg.OpenKey.__exit__ = mock.MagicMock()
        with _winreg.OpenKey as m:
            assert m == key

        _winreg.OpenKey.__enter__.assert_called_with()
        _winreg.OpenKey.__exit__.assert_called_with(None, None, None)
        _winreg.OpenKey.assert_called_with(_winreg.HKEY_LOCAL_MACHINE,
                                           self._winutils._config_key, 0,
                                           _winreg.KEY_ALL_ACCESS)

        _winreg.DeleteKey.assert_called_with(
            _winreg.OpenKey().__enter__(), self._SECTION)
        self.assertIsNone(response)

    def test_delete_config_value(self):
        key = mock.MagicMock()
        self._test_delete_config_value(key)

    def test_delete_config_value_error(self):
        self._test_delete_config_value(None)

    def _test_wait_for_boot_completion(self, ret_val):
        key = mock.MagicMock()
        _winreg.OpenKey = mock.MagicMock()
        _winreg.QueryValueEx = mock.MagicMock()

        time.sleep = mock.MagicMock()

        _winreg.QueryValueEx.side_effect = ret_val
        self._winutils.wait_for_boot_completion()
        _winreg.OpenKey.__enter__ = mock.MagicMock(return_value=key)
        _winreg.OpenKey.__exit__ = mock.MagicMock()
        with _winreg.OpenKey as m:
            assert m == key
        _winreg.OpenKey.__enter__.assert_called_with()
        _winreg.OpenKey.__exit__.assert_called_with(None, None, None)
        _winreg.OpenKey.assert_called_with(
            _winreg.HKEY_LOCAL_MACHINE,
            "SYSTEM\\Setup\\Status\\SysprepStatus", 0, _winreg.KEY_READ)

        _winreg.QueryValueEx.assert_called_with(
            _winreg.OpenKey().__enter__(), "GeneralizationState")

    def test_wait_for_boot_completion(self):
        ret_val = [[7]]
        self._test_wait_for_boot_completion(ret_val)

    def _test_stop_service(self, ret_val):
        if ret_val != 0:
            self.assertRaises(Exception, self._winutils._stop_service,
                              self._SERVICE_NAME)
        else:
            service = mock.MagicMock()
            wmi.WMI = mock.MagicMock(return_value=self._conn)

            self._conn.Win32_Service = mock.MagicMock(return_value=service)
            self._conn.Win32_Service(Name=self._SERVICE_NAME)
            service.StopService = mock.MagicMock(return_value=ret_val)

            self._winutils._stop_service(self._SERVICE_NAME)
            service.StopService.assert_called_with()
            self.assertEqual(service[0], self._SERVICE_NAME)

    def test_stop_service(self):
        ret_val = (0,)
        self._test_stop_service(ret_val)

    def test_stop_service_error(self):
        ret_val = (2,)
        self._test_stop_service(ret_val)

    def test_terminate(self):
        time.sleep = mock.MagicMock()
        self._winutils._stop_service = mock.MagicMock()

        self._winutils.terminate()

        self._winutils._stop_service.assert_called_with(self._SERVICE_NAME)
        time.sleep.assert_called_with(3)

    def _test_get_default_gateway(self, ip_gateway, interface_index):
        wmi.WMI = mock.MagicMock(return_value=self._conn)

        mock_net_adapter_config = mock.MagicMock()
        mock_net_adapter_config.DefaultIPGateway = [ip_gateway]
        self._conn.Win32_NetworkAdapterConfiguration.return_value = [
            mock_net_adapter_config]

        mock_net_adapter_config.InterfaceIndex = interface_index

        response = self._winutils.get_default_gateway()

        if ip_gateway:
            self.assertEqual(response, (1, ip_gateway))
        else:
            self.assertEqual(response, (None, None))

    def test_get_default_gateway(self):
        self._test_get_default_gateway(self._GATEWAY, 1)

    def test_get_default_gateway_error(self):
        self._test_get_default_gateway(None, None)

    def _test_check_static_route_exists(self, destination):
        wmi.WMI = mock.MagicMock(return_value=self._conn)

        if destination:
            self._conn.Win32_IP4RouteTable = mock.MagicMock(
                return_value='fake')
        else:
            self._conn.Win32_IP4RouteTable = mock.MagicMock(return_value='')

        response = self._winutils.check_static_route_exists(destination)

        self._conn.Win32_IP4RouteTable.assert_called_with(
            Destination=destination)

        if destination:
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_check_static_route_exists_true(self):
        self._test_check_static_route_exists(self._DESTINATION)

    def test_check_static_route_exists_false(self):
        self._test_check_static_route_exists(None)

    def _test_add_static_route(self, err):
        next_hop = '10.10.10.10'
        interface_index = 1
        metric = 9
        args = ['ROUTE', 'ADD', self._DESTINATION, 'MASK', self._NETMASK,
                next_hop]
        self._winutils.execute_process = mock.MagicMock(
            return_value=(None, err, None))
        if err:
            self.assertRaises(Exception, self._winutils.add_static_route,
                              self._DESTINATION, self._NETMASK, next_hop,
                              interface_index, metric)
        else:
            self._winutils.add_static_route(self._DESTINATION, self._NETMASK,
                                            next_hop, interface_index, metric)

            self._winutils.execute_process.assert_called_with(args)

    def test_add_static_route(self):
        self._test_add_static_route(err=404)

    def test_add_static_route_fail(self):
        self._test_add_static_route(None)

    def test_get_os_version(self):
        wmi.WMI = mock.MagicMock(return_value=self._conn)

        fake_os = mock.MagicMock()

        self._conn.Win32_OperatingSystem = mock.MagicMock(
            return_value=fake_os)
        fake_os[0].Version = '4.0'

        response = self._winutils.get_os_version()

        self.assertIsNotNone(response)

    def _test_get_volume_label(self, ret_val):
        label = mock.MagicMock()
        max_label_size = 261
        drive = 'Fake_drive'

        ctypes.create_unicode_buffer = mock.MagicMock(return_value=label)
        windll.kernel32.GetVolumeInformationW = mock.MagicMock(
            return_value=ret_val)

        response = self._winutils.get_volume_label(drive)

        if ret_val:
            self.assertIsNotNone(response)
        else:
            self.assertIsNone(response)

        ctypes.create_unicode_buffer.assert_called_with(max_label_size)
        windll.kernel32.GetVolumeInformationW.assert_called_with(
            drive, label, max_label_size, 0, 0, 0, 0, 0)

    def test_get_volume_label(self):
        self._test_get_volume_label('ret')

    def test_get_volume_label_no_return_value(self):
        self._test_get_volume_label(None)
