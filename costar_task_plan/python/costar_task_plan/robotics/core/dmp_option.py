
from dmp_policy import JointDmpPolicy, CartesianDmpPolicy

from costar_task_plan.abstract import AbstractOption

class DmpOption(AbstractOption):

  def __init__(self, policy_type, instances=[], attached_frame=None):
    if isinstance(policy_type, str):
      # parse into appropriate constructor
      if policy_type == 'joint':
        policy_type = JointDmpPolicy
        raise NotImplementedError('Joint space skills not currently implemented.')
      elif policy_type == 'cartesian':
        policy_type = CartesianDmpPolicy
      else:
        raise RuntimeError('invalid option for DMP policy type: %s'%policy_type)
    if not isinstance(policy_type, type):
      raise RuntimeError('invalid data type for DMP policy')

    self.policy_type = policy_type
    self.instances = []

  def makePolicy(self,):
    raise Exception('option.makePolicy not implemented!')

