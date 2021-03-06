# Copyright 2013 Mirantis Inc.
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

import os
import tempfile

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.plugins.windows import fileexecutils
from cloudbaseinit.plugins.windows.userdataplugins import base

LOG = logging.getLogger(__name__)


class ShellScriptPlugin(base.BaseUserDataPlugin):
    def __init__(self):
        super(ShellScriptPlugin, self).__init__("text/x-shellscript")

    def process(self, part):
        file_name = part.get_filename()
        target_path = os.path.join(tempfile.gettempdir(), file_name)

        try:
            with open(target_path, 'wb') as f:
                f.write(part.get_payload().encode())

            return fileexecutils.exec_file(target_path)
        except Exception as ex:
            LOG.warning('An error occurred during user_data execution: \'%s\''
                        % ex)
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)
