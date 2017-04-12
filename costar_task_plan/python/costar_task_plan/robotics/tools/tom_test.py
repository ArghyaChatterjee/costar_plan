#!/usr/bin/env python

# By Chris Paxton
# (c) 2017 The Johns Hopkins University
# See License for more details

from tom_oranges import MakeTomTaskModel, OrangesTaskArgs

from costar_task_plan.abstract import AbstractReward, AbstractFeatures
from costar_task_plan.mcts import DefaultTaskMctsPolicies, Node
from costar_task_plan.mcts import MonteCarloTreeSearch
from costar_task_plan.mcts import ExecutionPlan
from costar_task_plan.robotics.core import *
from costar_task_plan.robotics.tom import TomWorld
from costar_task_plan.tools import showTask

import rospy

def load_tom_world():
    return TomWorld('./',load_dataset=True)

class NullReward(AbstractReward):
    def __call__(self, world, *args, **kwargs):
      return 0., 0.
    def evaluate(self, world, *args, **kwargs):
      return 0., 0.
class NullFeatures(AbstractFeatures):
    def __call__(self, world, *args, **kwargs):
      return [0.]

# Main function:
# - create a TOM world
# - verify that the data is being managed correctly
# - fit models to data
# - create Reward objects as appropriate
# - create Policy objects as appropriate
def load_tom_data_and_run():

    import signal
    signal.signal(signal.SIGINT, exit)

    try:
      rospy.init_node('tom_test_node')
      world = load_tom_world()
      #world.makeRewardFunction("box")
      world.reward = NullReward()
      world.features = NullFeatures()
    except RuntimeError, e:
      print "Failed to create world. Are you in the right directory?"
      raise e

    # Set up the task model
    task = MakeTomTaskModel(world.lfd)
    args = OrangesTaskArgs()
    filled_args = task.compile(args)

    print "========================================"
    print task.nodeSummary()

    # Perform the search
    objects = ['box1', 'orange1', 'orange2', 'orange3', 'trash1',
            'squeeze_area1']

    path = do_search(world, task, objects)
    plan = ExecutionPlan(path)

    rate = rospy.Rate(1)
    try:
        while True:

            # Update observations about the world
            objects = ['box1', 'orange1', 'orange2', 'orange3', 'trash1',
                    'squeeze_area1']
            world.updateObservation(objects)

            # Pass a zero action down to the first actr, and only to the first actor.
            world.visualize()
            world.visualizePlan(plan)
            plan.step(world)

        rate.sleep()
    except rospy.ROSInterruptException, e:
        pass

def do_search(world, task, objects):

    policies = DefaultTaskMctsPolicies(task)
    #world.reward = LfdReward(world.lfd)
    search = MonteCarloTreeSearch(policies)

    objects = ['box1', 'orange1', 'orange2', 'orange3', 'trash1', 'squeeze_area1']
    world.updateObservation(objects)

    while len(world.observation) == 0:
        rospy.sleep(0.1)
        world.updateObservation(objects)

    print "================================================"
    print "Performing MCTS over options:"
    root = Node(world=world,root=True)
    elapsed, path = search(root,iter=10)
    print "-- ", elapsed, len(path)
    return path

if __name__ == "__main__":
    load_tom_data_and_run()



