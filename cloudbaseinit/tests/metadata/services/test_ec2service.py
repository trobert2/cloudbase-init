# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import mock
import posixpath
import unittest
import urllib2

from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import ec2service
from oslo.config import cfg

CONF = cfg.CONF


class EC2ServiceTest(unittest.TestCase):
    def setUp(self):
        CONF.set_override('retry_count_interval', 0)
        self._service = ec2service.EC2Service()

    @mock.patch('cloudbaseinit.utils.network.check_metadata_ip_route')
    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_data')
    def _test_load(self, mock_get_data, mock_check_metadata_ip_route,
                   side_effect):
        mock_get_data.side_effect = [side_effect]
        response = self._service.load()
        mock_check_metadata_ip_route.assert_called_once_with(
            CONF.ec2_metadata_base_url)
        mock_get_data.assert_called_once_with('latest/meta-data/')
        if side_effect is Exception:
            self.assertFalse(response)
        else:
            self.assertTrue(response)

    def test_load(self):
        self._test_load(side_effect=None)

    def test_load_exception(self):
        self._test_load(side_effect=Exception)

    @mock.patch('urllib2.urlopen')
    def _test_get_response(self, mock_urlopen, ret_value):
        req = mock.MagicMock()
        mock_urlopen.side_effect = [ret_value]
        is_instance = isinstance(ret_value, urllib2.HTTPError)
        if is_instance and ret_value.code == 404:
            self.assertRaises(base.NotExistingMetadataException,
                              self._service._get_response, req)
        elif is_instance and ret_value.code != 404:
            self.assertRaises(urllib2.HTTPError,
                              self._service._get_response, req)
        else:
            response = self._service._get_response(req)
            self.assertEqual(response, ret_value)
        mock_urlopen.assert_called_once_with(req)

    def test_get_response(self):
        self._test_get_response(ret_value=None)

    def test_get_response_error_404(self):
        err = urllib2.HTTPError("http://169.254.169.254/", 404,
                                'test error 404', {}, None)
        self._test_get_response(ret_value=err)

    def test_get_response_error_other(self):
        err = urllib2.HTTPError("http://169.254.169.254/", 409,
                                'test error 409', {}, None)
        self._test_get_response(ret_value=err)

    @mock.patch('urllib2.Request')
    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_response')
    def test_get_data(self, mock_get_response, mock_Request):
        response = self._service._get_data('fake')
        fake_path = posixpath.join(CONF.ec2_metadata_base_url, 'fake')
        mock_Request.assert_called_once_with(fake_path)
        mock_get_response.assert_called_once_with(mock_Request())
        self.assertEqual(response, mock_get_response().read())

    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_cache_data')
    def test_get_host_name(self, mock_get_cache_data):
        response = self._service.get_host_name()
        mock_get_cache_data.assert_called_once_with(
            '%s/meta-data/local-hostname' % self._service._metadata_version)
        self.assertEqual(response, mock_get_cache_data())

    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_cache_data')
    def test_get_instance_id(self, mock_get_cache_data):
        response = self._service.get_instance_id()
        mock_get_cache_data.assert_called_once_with(
            '%s/meta-data/instance-id' % self._service._metadata_version)
        self.assertEqual(response, mock_get_cache_data())

    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_cache_data')
    def test_get_public_keys(self, mock_get_cache_data):
        mock_get_cache_data.side_effect = ['key=info', 'fake key']
        response = self._service.get_public_keys()
        expected = [
            mock.call('%s/meta-data/public-keys' %
                      self._service._metadata_version),
            mock.call('%(version)s/meta-data/public-keys/%('
                      'idx)s/openssh-key' %
                      {'version': self._service._metadata_version,
                       'idx': 'key'})]
        self.assertEqual(mock_get_cache_data.call_args_list, expected)
        self.assertEqual(response, ['fake key'])
