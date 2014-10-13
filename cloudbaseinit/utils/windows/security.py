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

from six.moves import winreg


class WindowsSecurityUtils(object):
    _uac_key = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System"
    _uac_value_name = "LocalAccountTokenFilterPolicy"

    def __init__(self, osutils):
        self.osutils = osutils

    def set_local_account_token_filter_policy(self, enable=True):
        self.osutils._set_reg_key(self._uac_key,
                                  self._uac_value_name,
                                  int(enable))

    def get_local_account_token_filter_policy(self):
        key_name = self._uac_key
        name = self._uac_value_name
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                key_name) as key:
                (value, regtype) = winreg.QueryValueEx(key, name)
                return value
        except WindowsError:
            return False
