# Copyright 2018 The dm_control Authors.
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

"""Tests for Entity and Task hooks in an Environment."""

from absl.testing import absltest
from dm_control_m import composer
from dm_control_m.composer import hooks_test_utils
import numpy as np


class EnvironmentHooksTest(hooks_test_utils.HooksTestMixin, absltest.TestCase):

  def testEnvironmentHooksScheduling(self):
    env = composer.Environment(self.task)
    for hook_name in composer.HOOK_NAMES:
      env.add_extra_hook(hook_name, getattr(self.extra_hooks, hook_name))
    for _ in range(self.num_episodes):
      with self.track_episode():
        env.reset()
        for _ in range(self.steps_per_episode):
          env.step([0.1, 0.2, 0.3, 0.4])
          np.testing.assert_array_equal(env.physics.data.ctrl,
                                        [0.1, 0.2, 0.3, 0.4])


if __name__ == '__main__':
  absltest.main()
