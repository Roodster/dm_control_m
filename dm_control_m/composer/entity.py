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

"""Module defining the abstract entity class."""

import abc
import collections
import os
import weakref

from absl import logging
from dm_control_m import mjcf
from dm_control_m.composer import define
from dm_control_m.mujoco.wrapper import mjbindings
import numpy as np

_OPTION_KEYS = set(['update_interval', 'buffer_size', 'delay', 'aggregator',
                    'corruptor', 'enabled'])

_NO_ATTACHMENT_FRAME = 'No attachment frame found.'


# The component order differs from that used by the open-source `tf` package.
def _multiply_quaternions(quat1, quat2):
  result = np.empty_like(quat1)
  mjbindings.mjlib.mju_mulQuat(result, quat1, quat2)
  return result


def _rotate_vector(vec, quat):
  """Rotates a vector by the given quaternion."""
  result = np.empty_like(vec)
  mjbindings.mjlib.mju_rotVecQuat(result, vec, quat)
  return result


class _ObservableKeys:
  """Helper object that implements the `observables.dict_keys` functionality."""

  def __init__(self, entity, observables):
    self._entity = entity
    self._observables = observables

  def __getattr__(self, name):
    try:
      model_identifier = self._entity.mjcf_model.full_identifier
    except AttributeError as exc:
      raise ValueError(
          'cannot retrieve the full identifier of mjcf_model') from exc
    return os.path.join(model_identifier, name)

  def __dir__(self):
    out = set(self._observables.keys())
    out.update(dir(super()))
    return list(out)


class Observables:
  """Base-class for Entity observables.

  Subclasses should declare getter methods annotated with @define.observable
  decorator and returning an observable object.
  """

  def __init__(self, entity):
    self._entity = weakref.proxy(entity)

    self._observables = collections.OrderedDict()
    self._keys_helper = _ObservableKeys(self._entity, self._observables)

    # Ensure consistent ordering.
    for attr_name in sorted(dir(type(self))):
      type_attr = getattr(type(self), attr_name)
      if isinstance(type_attr, define.observable):
        self._observables[attr_name] = getattr(self, attr_name)

  @property
  def dict_keys(self):
    return self._keys_helper

  def as_dict(self, fully_qualified=True):
    """Returns an OrderedDict of observables belonging to this Entity.

    The returned observables will include any added using the _add_observable
    method, as well as any generated by a method decorated with the
    @define.observable annotation.

    Args:
      fully_qualified: (bool) Whether the dict keys should be prefixed with the
        parent entity's full model identifier.
    """

    if fully_qualified:
      # We need to make sure that this property doesn't raise an AttributeError,
      # otherwise __getattr__ is executed and we get a very funky error.
      try:
        model_identifier = self._entity.mjcf_model.full_identifier
      except AttributeError as exc:
        raise ValueError(
            'Cannot retrieve the full identifier of mjcf_model.') from exc

      return collections.OrderedDict(
          [(os.path.join(model_identifier, name), observable)
           for name, observable in self._observables.items()])
    else:
      # Return a copy to prevent dict being edited.
      return self._observables.copy()

  def get_observable(self, name, name_fully_qualified=False):
    """Returns the observable with the given name.

    Args:
      name: (str) The identifier of the observable.
      name_fully_qualified: (bool) Whether the provided name is prefixed by the
        model's full identifier.
    """

    if name_fully_qualified:
      try:
        model_identifier = self._entity.mjcf_model.full_identifier
      except AttributeError as exc:
        raise ValueError(
            'Cannot retrieve the full identifier of mjcf_model.') from exc
      return self._observables[name.replace(model_identifier, '')]
    else:
      return self._observables[name]

  def set_options(self, options):
    """Configure Observables with an options dict.

    Args:
      options: A dict of dicts of configuration options keyed on
        observable names, or a dict of configuration options, which will
        propagate those options to all observables.
    """
    if options is None:
      options = {}
    elif options.keys() and set(options.keys()).issubset(_OPTION_KEYS):
      options = dict([(key, options) for key in self._observables.keys()])

    for obs_key, obs_options in options.items():
      try:
        obs = self._observables[obs_key]
      except KeyError as exc:
        raise KeyError('No observable with name {!r}'.format(obs_key)) from exc
      obs.configure(**obs_options)

  def enable_all(self):
    """Enable all observables of this entity."""
    for obs in self._observables.values():
      obs.enabled = True

  def disable_all(self):
    """Disable all observables of this entity."""
    for obs in self._observables.values():
      obs.enabled = False

  def add_observable(self, name, observable, enabled=True):
    self._observables[name] = observable
    self._observables[name].enabled = enabled


class FreePropObservableMixin(metaclass=abc.ABCMeta):
  """Enforce observables of a free-moving object."""

  @property
  @abc.abstractmethod
  def position(self):
    pass

  @property
  @abc.abstractmethod
  def orientation(self):
    pass

  @property
  @abc.abstractmethod
  def linear_velocity(self):
    pass

  @property
  @abc.abstractmethod
  def angular_velocity(self):
    pass


class Entity(metaclass=abc.ABCMeta):
  """The abstract base class for an entity in a Composer environment."""

  def __init__(self, *args, **kwargs):
    """Entity constructor.

    Subclasses should not override this method, instead implement a _build
    method.

    Args:
      *args: Arguments passed through to the _build method.
      **kwargs: Keyword arguments. Passed through to the _build method, apart
        from the following.
          `observable_options`: A dictionary of Observable
            configuration options.
    """
    self._post_init_hooks = []

    self._parent = None
    self._attached = []

    try:
      observable_options = kwargs.pop('observable_options')
    except KeyError:
      observable_options = None

    self._build(*args, **kwargs)
    self._observables = self._build_observables()
    self._observables.set_options(observable_options)

  @abc.abstractmethod
  def _build(self, *args, **kwargs):
    """Entity initialization method to be overridden by subclasses."""
    raise NotImplementedError

  def _build_observables(self):
    """Entity observables initialization method.

    Returns:
      An object subclassing the Observables class.
    """
    return Observables(self)

  def iter_entities(self, exclude_self=False):
    """An iterator that recursively iterates through all attached entities.

    Args:
      exclude_self: (optional) Whether to exclude this `Entity` itself from the
        iterator.

    Yields:
      If `exclude_self` is `False`, the first value yielded is this Entity
      itself. The following Entities are then yielded recursively in a
      depth-first fashion, following the order in which the Entities are
      attached.
    """
    if not exclude_self:
      yield self
    for attached_entity in self._attached:
      for attached_entity_of_attached_entity in attached_entity.iter_entities():
        yield attached_entity_of_attached_entity

  @property
  def observables(self):
    """The observables defined by this entity."""
    return self._observables

  def initialize_episode_mjcf(self, random_state):
    """Callback executed when the MJCF model is modified between episodes."""
    pass

  def after_compile(self, physics, random_state):
    """Callback executed after the Mujoco Physics is recompiled."""
    pass

  def initialize_episode(self, physics, random_state):
    """Callback executed during episode initialization."""
    pass

  def before_step(self, physics, random_state):
    """Callback executed before an agent control step."""
    pass

  def before_substep(self, physics, random_state):
    """Callback executed before a simulation step."""
    pass

  def after_substep(self, physics, random_state):
    """A callback which is executed after a simulation step."""
    pass

  def after_step(self, physics, random_state):
    """Callback executed after an agent control step."""
    pass

  @property
  @abc.abstractmethod
  def mjcf_model(self):
    raise NotImplementedError

  def attach(self, entity, attach_site=None):
    """Attaches an `Entity` without any additional degrees of freedom.

    Args:
      entity: The `Entity` to attach.
      attach_site: (optional) The site to which to attach the entity's model. If
          not set, defaults to self.attachment_site.

    Returns:
      The frame of the attached model.
    """

    if attach_site is None:
      attach_site = self.attachment_site

    frame = attach_site.attach(entity.mjcf_model)
    self._attached.append(entity)
    entity._parent = weakref.ref(self)  # pylint: disable=protected-access
    return frame

  def detach(self):
    """Detaches this entity if it has previously been attached."""
    if self._parent is not None:
      parent = self._parent()  # pylint: disable=not-callable
      if parent:  # Weakref might dereference to None during garbage collection.
        self.mjcf_model.detach()
        parent._attached.remove(self)  # pylint: disable=protected-access
      self._parent = None
    else:
      raise RuntimeError('Cannot detach an entity that is not attached.')

  @property
  def parent(self):
    """Returns the `Entity` to which this entity is attached, or `None`."""
    return self._parent() if self._parent else None  # pylint: disable=not-callable

  @property
  def attachment_site(self):
    return self.mjcf_model

  @property
  def root_body(self):
    if self.parent:
      return mjcf.get_attachment_frame(self.mjcf_model)
    else:
      return self.mjcf_model.worldbody

  def global_vector_to_local_frame(self, physics, vec_in_world_frame):
    """Linearly transforms a world-frame vector into entity's local frame.

    Note that this function does not perform an affine transformation of the
    vector. In other words, the input vector is assumed to be specified with
    respect to the same origin as this entity's local frame. This function
    can also be applied to matrices whose innermost dimensions are either 2 or
    3. In this case, a matrix with the same leading dimensions is returned
    where the innermost vectors are replaced by their values computed in the
    local frame.

    Args:
      physics: An `mjcf.Physics` instance.
      vec_in_world_frame: A NumPy array with last dimension of shape (2,) or
      (3,) that represents a vector quantity in the world frame.

    Returns:
      The same quantity as `vec_in_world_frame` but reexpressed in this
      entity's local frame. The returned np.array has the same shape as
      np.asarray(vec_in_world_frame).

    Raises:
      ValueError: if `vec_in_world_frame` does not have shape ending with (2,)
        or (3,).
    """
    vec_in_world_frame = np.asarray(vec_in_world_frame)

    xmat = np.reshape(physics.bind(self.root_body).xmat, (3, 3))
    # The ordering of the np.dot is such that the transformation holds for any
    # matrix whose final dimensions are (2,) or (3,).
    if vec_in_world_frame.shape[-1] == 2:
      return np.dot(vec_in_world_frame, xmat[:2, :2])
    elif vec_in_world_frame.shape[-1] == 3:
      return np.dot(vec_in_world_frame, xmat)
    else:
      raise ValueError('`vec_in_world_frame` should have shape with final '
                       'dimension 2 or 3: got {}'.format(
                           vec_in_world_frame.shape))

  def global_xmat_to_local_frame(self, physics, xmat):
    """Transforms another entity's `xmat` into this entity's local frame.

    This function takes another entity's (E) xmat, which is an SO(3) matrix
    from E's frame to the world frame, and turns it to a matrix that transforms
    from E's frame into this entity's local frame.

    Args:
      physics: An `mjcf.Physics` instance.
      xmat: A NumPy array of shape (3, 3) or (9,) that represents another
        entity's xmat.

    Returns:
      The `xmat` reexpressed in this entity's local frame. The returned
      np.array has the same shape as np.asarray(xmat).

    Raises:
      ValueError: if `xmat` does not have shape (3, 3) or (9,).
    """
    xmat = np.asarray(xmat)

    input_shape = xmat.shape
    if xmat.shape == (9,):
      xmat = np.reshape(xmat, (3, 3))

    self_xmat = np.reshape(physics.bind(self.root_body).xmat, (3, 3))
    if xmat.shape == (3, 3):
      return np.reshape(np.dot(self_xmat.T, xmat), input_shape)
    else:
      raise ValueError('`xmat` should have shape (3, 3) or (9,): got {}'.format(
          xmat.shape))

  def get_pose(self, physics):
    """Get the position and orientation of this entity relative to its parent.

    Note that the semantics differ slightly depending on whether or not the
    entity has a free joint:

    * If it has a free joint the position and orientation are always given in
      global coordinates.
    * If the entity is fixed or attached with a different joint type then the
      position and orientation are given relative to the parent frame.

    For entities that are either attached directly to the worldbody, or to other
    entities that are positioned at the global origin (e.g. the arena) the
    global and relative poses are equivalent.

    Args:
      physics: An instance of `mjcf.Physics`.

    Returns:
      A 2-tuple where the first entry is a (3,) numpy array representing the
      position and the second is a (4,) numpy array representing orientation as
      a quaternion.

    Raises:
      RuntimeError: If the entity is not attached.
    """
    root_joint = mjcf.get_frame_freejoint(self.mjcf_model)
    if root_joint:
      position = physics.bind(root_joint).qpos[:3]
      quaternion = physics.bind(root_joint).qpos[3:]
    else:
      attachment_frame = mjcf.get_attachment_frame(self.mjcf_model)
      if attachment_frame is None:
        raise RuntimeError(_NO_ATTACHMENT_FRAME)
      position = physics.bind(attachment_frame).pos
      quaternion = physics.bind(attachment_frame).quat
    return position, quaternion

  def set_pose(self, physics, position=None, quaternion=None):
    """Sets position and/or orientation of this entity relative to its parent.

    If the entity is attached with a free joint, this method will set the
    respective DoFs of the joint. If the entity is either fixed or attached with
    a different joint type, this method will update the position and/or
    quaternion of the attachment frame.

    Note that the semantics differ slightly between the two cases: the DoFs of a
    free body are specified in global coordinates, whereas the position of a
    non-free body is specified in relative coordinates with respect to the
    parent frame. However, for entities that are either attached directly to the
    worldbody, or to other entities that are positioned at the global origin
    (e.g. the arena), there is no difference between the two cases.

    Args:
      physics: An instance of `mjcf.Physics`.
      position: (optional) A NumPy array of size 3.
      quaternion: (optional) A NumPy array of size 4.

    Raises:
      RuntimeError: If the entity is not attached.
    """
    root_joint = mjcf.get_frame_freejoint(self.mjcf_model)
    if root_joint:
      if position is not None:
        physics.bind(root_joint).qpos[:3] = position
      if quaternion is not None:
        physics.bind(root_joint).qpos[3:] = quaternion
    else:
      attachment_frame = mjcf.get_attachment_frame(self.mjcf_model)
      if attachment_frame is None:
        raise RuntimeError(_NO_ATTACHMENT_FRAME)
      if position is not None:
        physics.bind(attachment_frame).pos = position
      if quaternion is not None:
        normalised_quaternion = quaternion / np.linalg.norm(quaternion)
        physics.bind(attachment_frame).quat = normalised_quaternion

  def shift_pose(self,
                 physics,
                 position=None,
                 quaternion=None,
                 rotate_velocity=False):
    """Shifts the position and/or orientation from its current configuration.

    This is a convenience function that performs the same operation as
    `set_pose`, but where the specified `position` is added to the current
    position, and the specified `quaternion` is premultiplied to the current
    quaternion.

    Args:
      physics: An instance of `mjcf.Physics`.
      position: (optional) A NumPy array of size 3.
      quaternion: (optional) A NumPy array of size 4.
      rotate_velocity: (optional) A bool, whether to shift the current linear
        velocity along with the pose. This will rotate the current linear
        velocity, which is expressed relative to the world frame. The angular
        velocity, which is expressed relative to the local frame is left
        unchanged.

    Raises:
      RuntimeError: If the entity is not attached.
    """
    current_position, current_quaternion = self.get_pose(physics)
    new_position, new_quaternion = None, None
    if position is not None:
      new_position = current_position + position
    if quaternion is not None:
      quaternion = np.array(quaternion, dtype=np.float64, copy=False)
      new_quaternion = _multiply_quaternions(quaternion, current_quaternion)
      root_joint = mjcf.get_frame_freejoint(self.mjcf_model)
      if root_joint and rotate_velocity:
        # Rotate the linear velocity. The angular velocity (qvel[3:])
        # is left unchanged, as it is expressed in the local frame.
        # When rotatating the body frame the angular velocity already
        # tracks the rotation but the linear velocity does not.
        velocity = physics.bind(root_joint).qvel[:3]
        rotated_velocity = _rotate_vector(velocity, quaternion)
        self.set_velocity(physics, rotated_velocity)
    self.set_pose(physics, new_position, new_quaternion)

  def get_velocity(self, physics):
    """Gets the linear and angular velocity of this free entity.

    Args:
      physics: An instance of `mjcf.Physics`.

    Returns:
      A 2-tuple where the first entry is a (3,) numpy array representing the
      linear velocity and the second is a (3,) numpy array representing the
      angular velocity.

    """
    root_joint = mjcf.get_frame_freejoint(self.mjcf_model)
    if root_joint:
      velocity = physics.bind(root_joint).qvel[:3]
      angular_velocity = physics.bind(root_joint).qvel[3:]
      return velocity, angular_velocity
    else:
      raise ValueError('get_velocity cannot be used on a non-free entity')

  def set_velocity(self, physics, velocity=None, angular_velocity=None):
    """Sets the linear velocity and/or angular velocity of this free entity.

    If the entity is attached with a free joint, this method will set the
    respective DoFs of the joint. Otherwise a warning is logged.

    Args:
      physics: An instance of `mjcf.Physics`.
      velocity: (optional) A NumPy array of size 3 specifying the
        linear velocity.
      angular_velocity: (optional) A NumPy array of size 3 specifying the
        angular velocity
    """
    root_joint = mjcf.get_frame_freejoint(self.mjcf_model)
    if root_joint:
      if velocity is not None:
        physics.bind(root_joint).qvel[:3] = velocity
      if angular_velocity is not None:
        physics.bind(root_joint).qvel[3:] = angular_velocity
    else:
      logging.warning('Cannot set velocity on Entity with no free joint.')

  def configure_joints(self, physics, position):
    """Configures this entity's internal joints.

    The default implementation of this method simply sets the `qpos` of all
    joints in this entity to the values specified in the `position` argument.
    Entity subclasses with actuated joints may override this method to achieve a
    stable reconfiguration of joint positions, for example the control signal
    of position actuators may be changed to match the new joint positions.

    Args:
      physics: An instance of `mjcf.Physics`.
      position: The desired position of this entity's joints.
    """
    joints = self.mjcf_model.find_all('joint', exclude_attachments=True)
    physics.bind(joints).qpos = position


class ModelWrapperEntity(Entity):
  """An entity class that wraps an MJCF model without any additional logic."""

  def _build(self, mjcf_model):
    self._mjcf_model = mjcf_model

  @property
  def mjcf_model(self):
    return self._mjcf_model
