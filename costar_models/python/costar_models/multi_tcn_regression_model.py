from __future__ import print_function

import keras.backend as K
import keras.losses as losses
import keras.optimizers as optimizers
import numpy as np

from collections import deque
from keras.layers.advanced_activations import LeakyReLU
from keras.layers import Input, RepeatVector, Reshape
from keras.layers import UpSampling2D, Conv2DTranspose
from keras.layers import BatchNormalization, Dropout
from keras.layers import Dense, Conv2D, Activation, Flatten
from keras.layers.merge import Concatenate
from keras.losses import binary_crossentropy
from keras.models import Model, Sequential
from keras.optimizers import Adam
from matplotlib import pyplot as plt

from .abstract import AbstractAgentBasedModel
from .robot_multi_models import *

class RobotMultiTCNRegression(AbstractAgentBasedModel):
    '''
    Create regression model that looks at multiple time slices to compute the
    best next action from the training data set.
    '''


    def __init__(self, taskdef, *args, **kwargs):
        '''
        Read in taskdef for this model (or set of models). Use it to create the
        regression neural net that we can fit to compute our next action.

        Remember, here the "labels" are computed from the task model. We can
        use images and joint states together to compute next image or next
        joint state.
        '''

        super(RobotMultiTCNRegression, self).__init__(*args, **kwargs)

        self.taskdef = taskdef
        self.model = None
        
        self.dropout_rate = 0.5
        
        self.num_filters = 128
        self.combined_dense_size = 128

        self.num_frames = 10
        self.tcn_filters = 128
        self.num_tcn_levels = 2
        self.tcn_dense_size = 1024

        self.buffer_img = []
        self.buffer_arm = []
        self.buffer_gripper = []

        self.imgs = deque()
        self.q = deque()
        self.gripper = deque()

    def _makeModel(self, features, arm, gripper, arm_cmd, gripper_cmd,
            *args, **kwargs):
        '''
        We will either receive:
            (n_samples, window_size,) + feature_shape
        Or:
            (n_samples = 1, ) + feature_shape

        Depending on if we are in train or test mode.
        '''
        img_shape = features.shape[1:]
        if len(img_shape) == 3:
            img_shape = (self.num_frames,) + img_shape
        arm_size = arm.shape[-1]
        if len(gripper.shape) > 1:
            gripper_size = gripper.shape[-1]
        else:
            gripper_size = 1

        ins, x = GetEncoder3D(img_shape, arm_size, gripper_size,
                self.dropout_rate,
                filters=self.num_filters,
                pre_tiling_layers=1,
                post_tiling_layers=3,
                kernel_size=[3,3,3],
                time_distributed=self.num_frames,
                dropout=True,
                leaky=True,
                tile=True,
                )
        x = Flatten()(x)
        x = Dense(self.combined_dense_size)(x)
        
        arm_out = Dense(arm_size)(x)
        gripper_out = Dense(gripper_size)(x)

        model = Model(ins, [arm_out, gripper_out])
        #model = Model(img_ins, [arm_out])
        optimizer = self.getOptimizer()
        model.compile(loss="mse", optimizer=optimizer)
        self.model = model

    def train(self, features, arm, gripper, arm_cmd, gripper_cmd, example,
            label,
            *args, **kwargs):
        '''
        Training data -- just direct regression based on MSE from the other
        trajectory.
        '''

        [features, arm, gripper, arm_cmd, gripper_cmd] = \
                SplitIntoChunks(
                        datasets=[features, arm, gripper, arm_cmd, gripper_cmd],
                        labels=example,
                        reward=None,
                        chunk_length=self.num_frames,
                        front_padding=False,
                        rear_padding=True)

        arm_cmd_target = LastInChunk(arm_cmd)
        gripper_cmd_target = LastInChunk(gripper_cmd)

        self._makeModel(features, arm, gripper, arm_cmd,
                gripper_cmd, *args, **kwargs)
        self.model.summary()
        self.model.fit(
                x=[features, arm, gripper],
                y=[arm_cmd_target, gripper_cmd_target],
                epochs=self.epochs,
                initial_epoch=self.initial_epoch,
                batch_size=self.batch_size,
                )

    def plot(self):
        pass

    def predict(self, world):
        world.history_length = self.num_frames
        if self.model is None:
            raise RuntimeError('model is missing')

        '''
        Store or create the set of input features we need for the TCN
        '''
        features = world.getHistoryMatrix() # use cached features
        if isinstance(features, list):
            assert len(features) == len(self.model.inputs)
        if self.model is None:
            raise RuntimeError('model is missing')
        features = [f.reshape((1,)+f.shape) for f in features]
        res = self.model.predict(features)
        print(res)
        return res

