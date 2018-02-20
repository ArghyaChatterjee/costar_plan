#!/usr/bin/env python

from __future__ import print_function

import matplotlib as mpl
#mpl.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

from costar_models import *
from costar_models.sampler2 import PredictionSampler2
from costar_models.datasets.npz import NpzDataset
from costar_models.datasets.npy_generator import NpzGeneratorDataset
from costar_models.datasets.h5f_generator import H5fGeneratorDataset


def visualizeHiddenMain(args):
    '''
    Tool for running model training without the rest of the simulation/planning/ROS
    code. This should be more or less independent and only rely on a couple
    external features.
    '''
    ConfigureGPU(args)

    data_file_info = args['data_file'].split('.')
    data_type = data_file_info[-1]
    root = ""
    for i, tok in enumerate(data_file_info[:-1]):
        if i < len(data_file_info)-1 and i > 0:
            root += '.'
        root += tok
    if data_type == "npz":
        dataset = NpzGeneratorDataset(root)
        data = dataset.load(success_only = args['success_only'])
    elif data_type == "h5f":
        dataset = H5fGeneratorDataset(root)
        data = dataset.load(success_only = args['success_only'])
    else:
        raise NotImplementedError('data type not implemented: %s'%data_type)

    if 'model' in args and args['model'] is not None:
        model = MakeModel(taskdef=None, **args)
        model.validate = True
        model.load(world=None,**data)
        train_generator = model.trainGenerator(dataset)
        test_generator = model.testGenerator(dataset)

        data = next(test_generator)
        features, targets = next(train_generator)
        [I0, I, o1, o2, oin] = features
        [ I_target, I_target2, o1_1h, v, qa, ga, o2_1h] = targets

        # Same as in training code
        model.model.predict([I0, I, o1, o2, oin])
        h = model.encode(I)
        h0 = model.encode(I0)
        prev_option = model.prevOption(features)
        null_option = np.ones_like(prev_option) * model.null_option
        p_a = model.pnext(h0, h, prev_option)
        v = model.value(h0, h)

        print(I.shape, h.shape)
        if not h.shape[0] == I.shape[0]:
            raise RuntimeError('something went wrong with dimensions')
        print("shape =", p_a.shape)
        action = np.argmax(p_a,axis=1)
        print (o1)
        print(prev_option)
        print(action)
        h_goal = model.transform(h0, h0, o1)
        img_goal = model.decode(h_goal)
        v_goal = model.value(h0, h_goal)
        print("--------------\nHidden state:\n--------------\n")
        print("shape of hidden samples =", h.shape)
        print("shape of images =", I.shape)
        for i in range(h.shape[0]):
            print("------------- %d -------------"%i)
            print("prev option =", prev_option[i])
            print("best option =", np.argmax(p_a[i]))
            print("actual option=", o1[i])
            print("value =", v[i])
            print("goal value =", v_goal[i])
            print(p_a[i])
            plt.figure()
            plt.subplot(1,5,1)
            Show(I[i])
            plt.subplot(1,5,2)
            Show(np.squeeze(h[i,:,:,:3]))
            plt.subplot(1,5,3)
            Show(np.squeeze(h_goal[i,:,:,:3]))
            plt.subplot(1,5,4)
            Show(img_goal[i])
            plt.subplot(1,5,5)
            Show(targets[0][i])
            plt.show()

    else:
        raise RuntimeError('Must provide a model to load')

if __name__ == '__main__':
    args = ParseModelArgs()
    if args['profile']:
        import cProfile
        cProfile.run('main(args)')
    else:
        visualizeHiddenMain(args)
