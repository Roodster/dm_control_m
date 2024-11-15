# Copyright 2020 The dm_control Authors.
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
"""Tests for the Jumping Ball."""


from absl.testing import absltest
from absl.testing import parameterized
from dm_control_m import composer
from dm_control_m import mjcf
from dm_control_m.composer.observation.observable import base as observable_base
from dm_control_m.locomotion.arenas import corridors as corr_arenas
from dm_control_m.locomotion.tasks import corridors as corr_tasks
from dm_control_m.locomotion.walkers import jumping_ball
import numpy as np

_CONTROL_TIMESTEP = .02
_PHYSICS_TIMESTEP = 0.005


def _get_jumping_ball_corridor_physics():
  walker = jumping_ball.JumpingBallWithHead()
  arena = corr_arenas.EmptyCorridor()
  task = corr_tasks.RunThroughCorridor(
      walker=walker,
      arena=arena,
      walker_spawn_position=(5, 0, 0),
      walker_spawn_rotation=0,
      physics_timestep=_PHYSICS_TIMESTEP,
      control_timestep=_CONTROL_TIMESTEP)

  env = composer.Environment(
      time_limit=30,
      task=task,
      strip_singleton_obs_buffer_dim=True)

  return walker, env


class JumpingBallWithHeadTest(parameterized.TestCase):

  def test_can_compile_and_step_simulation(self):
    _, env = _get_jumping_ball_corridor_physics()
    physics = env.physics
    for _ in range(100):
      physics.step()

  @parameterized.parameters([
      'egocentric_camera',
  ])
  def test_get_element_property(self, name):
    attribute_value = getattr(jumping_ball.JumpingBallWithHead(), name)
    self.assertIsInstance(attribute_value, mjcf.Element)

  @parameterized.parameters([
      'actuators',
      'end_effectors',
      'observable_joints',
  ])
  def test_get_element_tuple_property(self, name):
    attribute_value = getattr(jumping_ball.JumpingBallWithHead(), name)
    self.assertNotEmpty(attribute_value)
    for item in attribute_value:
      self.assertIsInstance(item, mjcf.Element)

  def test_set_name(self):
    name = 'fred'
    walker = jumping_ball.JumpingBallWithHead(name=name)
    self.assertEqual(walker.mjcf_model.model, name)

  @parameterized.parameters(
      'sensors_velocimeter',
      'world_zaxis',
  )
  def test_evaluate_observable(self, name):
    walker, env = _get_jumping_ball_corridor_physics()
    physics = env.physics
    observable = getattr(walker.observables, name)
    observation = observable(physics)
    self.assertIsInstance(observation, (float, np.ndarray))

  def test_proprioception(self):
    walker = jumping_ball.JumpingBallWithHead()
    for item in walker.observables.proprioception:
      self.assertIsInstance(item, observable_base.Observable)

  @parameterized.parameters(
      dict(camera_control=True, add_ears=True, camera_height=1.),
      dict(camera_control=True, add_ears=False, camera_height=1.),
      dict(camera_control=False, add_ears=True, camera_height=1.),
      dict(camera_control=False, add_ears=False, camera_height=1.),
      dict(camera_control=True, add_ears=True, camera_height=None),
      dict(camera_control=True, add_ears=False, camera_height=None),
      dict(camera_control=False, add_ears=True, camera_height=None),
      dict(camera_control=False, add_ears=False, camera_height=None),
      )
  def test_instantiation(self, camera_control, add_ears, camera_height):
    jumping_ball.JumpingBallWithHead(camera_control=camera_control,
                                     add_ears=add_ears,
                                     camera_height=camera_height)

if __name__ == '__main__':
  absltest.main()
