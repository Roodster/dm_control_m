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

"""Meta-variations that modify original values by a specified variation."""


from dm_control_m.composer.variation import base
from dm_control_m.composer.variation import variation_values


class Additive(base.Variation):
  """A variation that adds to an existing value.

  This variation takes a value generated by another variation and adds it to an
  existing value. In cumulative mode, the generated value is added to the
  current value being varied. In non-cumulative mode, the generated value is
  added to a fixed initial value.
  """

  def __init__(self, variation, cumulative=False):
    self._variation = variation
    self._cumulative = cumulative

  def __call__(self, initial_value=None, current_value=None, random_state=None):
    base_value = current_value if self._cumulative else initial_value
    return base_value + (
        variation_values.evaluate(self._variation, initial_value, current_value,
                                  random_state))


class Multiplicative(base.Variation):
  """A variation that multiplies to an existing value.

  This variation takes a value generated by another variation and multiplies it
  to an existing value. In cumulative mode, the generated value is multiplied to
  the current value being varied. In non-cumulative mode, the generated value is
  multiplied to a fixed initial value.
  """

  def __init__(self, variation, cumulative=False):
    self._variation = variation
    self._cumulative = cumulative

  def __call__(self, initial_value=None, current_value=None, random_state=None):
    base_value = current_value if self._cumulative else initial_value
    return base_value * (
        variation_values.evaluate(self._variation, initial_value, current_value,
                                  random_state))
