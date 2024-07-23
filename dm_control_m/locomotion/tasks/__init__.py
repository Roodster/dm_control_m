# Copyright 2019 The dm_control Authors.
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
"""Tasks in the Locomotion library."""


from dm_control_M.locomotion.tasks.corridors import RunThroughCorridor
from dm_control_M.locomotion.tasks.escape import Escape
# Import1 removed.
# Import2 removed.
from dm_control_M.locomotion.tasks.go_to_target import GoToTarget
from dm_control_M.locomotion.tasks.random_goal_maze import ManyGoalsMaze
from dm_control_M.locomotion.tasks.random_goal_maze import ManyHeterogeneousGoalsMaze
from dm_control_M.locomotion.tasks.random_goal_maze import RepeatSingleGoalMaze
from dm_control_M.locomotion.tasks.random_goal_maze import RepeatSingleGoalMazeAugmentedWithTargets
from dm_control_M.locomotion.tasks.reach import TwoTouch
