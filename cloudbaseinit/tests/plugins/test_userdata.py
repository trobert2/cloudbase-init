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

import email
import mock
import os
import re
import tempfile
import unittest
import uuid

from cloudbaseinit.metadata.services import base as metadata_services_base
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.osutils import windows
from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import userdata


class TestUserDataPlugin(unittest.TestCase):
    '''testing the userdata module'''

    def setUp(self):
        #userdata_plugins.PluginSet.reload = mock.MagicMock()
        self.plugin = userdata.UserDataPlugin()
        self.service = metadata_services_base.BaseMetadataService()

    def test_no_user_data(self):
        self.service.get_user_data = mock.MagicMock(return_value=None)
        response = self.plugin.execute(self.service)
        self.service.get_user_data.assert_called_with('openstack')
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_get_user_data_exception(self):
        self.side_effect = metadata_services_base.NotExistingMetadataException
        self.service.get_user_data = mock.MagicMock(
            side_effect=self.side_effect)
        response = self.plugin.execute(self.service)
        self.service.get_user_data.assert_called_with('openstack')
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_get_proper_user_data(self):
        self.service.get_user_data = mock.MagicMock(return_value='rem cmd')
        self.plugin._process_userdata = mock.Mock()
        response = self.plugin.execute(self.service)
        self.service.get_user_data.assert_called_with('openstack')
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))
        self.plugin._process_userdata.assert_called_with('rem cmd')

    def test_process_multipart_userdata(self):
        self.fake_user_data = 'Content-Type: multipart'
        self.plugin._process_part = mock.Mock()
        self.plugin._process_userdata(self.fake_user_data)
        self.plugin._process_part.assert_called_once()

    def test_process_singlepart_userdata(self):
        self.fake_user_data = 'rem cmd'
        userdata.handle = mock.Mock()
        self.plugin._process_userdata(self.fake_user_data)
        userdata.handle.assert_called_with('rem cmd')

    def _test_process_part(self, part):
        part_handler = mock.MagicMock()
        self.plugin._get_part_handler = mock.MagicMock(
            return_value=part_handler)
        self.plugin._begin_part_process_event = mock.MagicMock()
        self.plugin._end_part_process_event = mock.MagicMock()
        if part:
            self.plugin._process_part(part)

            self.plugin._get_part_handler.assert_called_with(part)
            self.plugin._begin_part_process_event.assert_called_with(part)
            part_handler.process.assert_called_with(part)
            self.plugin._end_part_process_event.assert_called_with(part)
        else:
            self.assertRaises(Exception, self.plugin._process_part)

    def test_process_part(self):
        part = mock.MagicMock()
        self._test_process_part(part)

    def test_process_part_exception(self):
        self._test_process_part(None)

    def _test_begin_part_process_event(self, part):
        handler = mock.MagicMock()
        if not part:
            self.assertRaises(Exception,
                              self.plugin._begin_part_process_event)
        else:
            self.plugin._get_custom_handler = mock.MagicMock(
                return_value=handler)

            self.plugin._begin_part_process_event(part)
            part.get_filename.assert_called_with()
            part.get_payloadassert_called_with()
            handler.assert_called_with("", "__begin__", part.get_filename(),
                                       part.get_payload())
            self.plugin._get_custom_handler.assert_called_with(part)

    def test_begin_part_process_event(self):
        part = mock.Mock()
        self._test_begin_part_process_event(part)

    def test_begin_part_process_event_fail(self):
        self._test_begin_part_process_event(None)

    def _test_end_part_process_event(self, part):
        handler = mock.MagicMock()
        if not part:
            self.assertRaises(Exception,
                              self.plugin._begin_part_process_event)
        else:
            self.plugin._get_custom_handler = mock.MagicMock(
                return_value=handler)

            self.plugin._end_part_process_event(part)
            part.get_filename.assert_called_with()
            part.get_payloadassert_called_with()
            handler.assert_called_with("", "__end__", part.get_filename(),
                                       part.get_payload())
            self.plugin._get_custom_handler.assert_called_with(part)

    def test_end_part_process_event(self):
        part = mock.Mock()
        self._test_begin_part_process_event(part)

    def test_end_part_process_event_fail(self):
        self._test_begin_part_process_event(None)

    def test_get_custom_handler(self):
        part = mock.MagicMock()
        self.plugin.plugin_set = mock.MagicMock()
        self.plugin.plugin_set.reload = mock.MagicMock()
        self.plugin.plugin_set.has_custom_handlers = True
        self.plugin.plugin_set.custom_handlers = {'fake': 'fake'}
        part.get_content_type = mock.MagicMock(return_value='fake')

        response = self.plugin._get_custom_handler(part)

        self.assertIsNotNone(response)

    def test_get_part_handler(self):
        part = mock.MagicMock()
        self.plugin.plugin_set = mock.MagicMock()
        self.plugin.plugin_set.reload = mock.MagicMock()
        self.plugin.plugin_set.set = {'fake': 'fake'}
        part.get_content_type = mock.MagicMock(return_value='fake')

        response = self.plugin._get_part_handler(part)

        self.assertIsNotNone(response)

    def test_parse_mime(self):
        fake_user_data = '#ps1: fake command'
        msg = mock.MagicMock()
        email.message_from_string = mock.MagicMock(return_value=msg)
        msg.walk = mock.MagicMock()

        response = self.plugin._parse_mime(fake_user_data)

        email.message_from_string.assert_called_with(fake_user_data)
        self.assertIsNotNone(response)

    def _test_handle(self, fake_user_data, directory_exists=True):
        tempfile.gettempdir = mock.MagicMock()
        uuid.uuid4 = mock.MagicMock(return_value='randomID')
        os.path.join = mock.MagicMock(return_value='fake_temp\\randomID')
        match_instance = mock.MagicMock()
        path = 'fake_temp\\randomID'
        args = None

        if fake_user_data == '^rem cmd\s':
            side_effect = [match_instance]
            number_of_calls = 1
            extension = '.cmd'
            args = [path+extension]
            shell = True
        elif fake_user_data == '#!':
            side_effect = [None, match_instance]
            number_of_calls = 2
            extension = '.sh'
            args = ['bash.exe', path+extension]
            shell = False
        elif fake_user_data == '#ps1\s':
            side_effect = [None, None, match_instance]
            number_of_calls = 3
            extension = '.ps1'
            args = ['powershell.exe', '-ExecutionPolicy', 'RemoteSigned',
                    '-NonInteractive', path+extension]
            shell = False
        else:
            os.path.expandvars = mock.MagicMock()
            side_effect = [None, None, None, match_instance]
            number_of_calls = 4
            extension = '.ps1'
            shell = False
            if directory_exists:
                args = [os.path.expandvars('%windir%\\sysnative\\'
                                           'WindowsPowerShell\\v1.0\\'
                                           'powershell.exe'),
                        '-ExecutionPolicy',
                        'RemoteSigned', '-NonInteractive', path+extension]
                os.path.isdir = mock.MagicMock(return_value=True)
            else:
                os.path.isdir = mock.MagicMock(return_value=False)

        re.search = mock.MagicMock(side_effect=side_effect)
        os.remove = mock.MagicMock()
        windows.WindowsUtils.execute_process = mock.MagicMock()

        os.path.exists = mock.MagicMock()
        with mock.patch('cloudbaseinit.plugins.windows.userdata.open',
                        mock.mock_open(), create=True):
            response = userdata.handle(fake_user_data)

        tempfile.gettempdir.assert_called_once_with()

        os.path.join.assert_called_once_with(tempfile.gettempdir(),
                                             str(uuid.uuid4()))
        assert re.search.call_count == number_of_calls
        if args:
            windows.WindowsUtils.execute_process.assert_called_with(args,
                                                                    shell)

        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_handle_batch(self):
        fake_user_data = '^rem cmd\s'
        self._test_handle(fake_user_data)

    def test_handle_shell(self):
        fake_user_data = '^#!'
        self._test_handle(fake_user_data)

    def test_handle_powershell(self):
        fake_user_data = '^#ps1\s'
        self._test_handle(fake_user_data)

    def test_handle_powershell_sysnative(self):
        fake_user_data = '#ps1_sysnative\s'
        self._test_handle(fake_user_data)

    def test_handle_powershell_sysnative_no_sysnative(self):
        fake_user_data = '#ps1_sysnative\s'
        self._test_handle(fake_user_data, False)
