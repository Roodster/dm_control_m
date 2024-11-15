# Copyright 2017 The dm_control Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

"""Assets used for testing the MuJoCo bindings."""

import os

from dm_control_m.utils import io as resources

_ASSETS_DIR = os.path.dirname(__file__)


def get_contents(filename):
  """Returns the contents of an asset as a string."""
  return resources.GetResource(os.path.join(_ASSETS_DIR, filename), mode='rb')


def get_path(filename):
  """Returns the path to an asset."""
  return resources.GetResourceFilename(os.path.join(_ASSETS_DIR, filename))
