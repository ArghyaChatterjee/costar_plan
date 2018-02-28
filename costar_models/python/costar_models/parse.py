
from .util import GetModels

import argparse
import sys

_desc = """
Start the model learning tool. This should be independent of the actual
simulation capabilities we are using.
"""
_epilog = """
"""

def GetAvailableFeatures():
    '''
    List all the possible sets of features we might recognize when constructing
    a model using the tool.
    '''
    return ['empty',
            'null',
            'husky',
            'jigsaws',
            'depth', # depth channel only
            'rgb', # RGB channels only
            'joint_state', # robot joints only
            'multi', # RGB+joints+gripper
            'pose', #object poses + joints + gripper
            'grasp_segmentation',]

def GetModelParser():
    '''
    Get the set of arguments for models and learning.
    '''
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-L', '--lr', '--learning_rate',
                        help="Learning rate to be used in algorithm.",
                        type=float,
                        default=1e-3)
    parser.add_argument('--model_directory',
                        help="models directory",
                        default = "~/.costar/models")
    parser.add_argument('--reqs_directory',
                        help="directory for reading in required submodels",
                        type = str,
                        default = None)
    parser.add_argument('-i', '--iter',
                        help='Number of iterations to run',
                        default=100,
                        type=int)
    parser.add_argument('-b','--batch_size',
                        help='Batch size to use in the model',
                        default=64,
                        type=int)
    parser.add_argument('-e','--epochs',
                        help="Number of epochs",
                        type=int,
                        default=500,)
    parser.add_argument('--initial_epoch',
                        help="Where to start counting epochs",
                        type=int,
                        default=0) # epoch 0 = 1
    parser.add_argument('--data_file', '--file',
                        help="File name for data archive.",
                        default='data.npz')
    parser.add_argument('--model_descriptor',
                        help="model description for use with save/load file",
                        default="model")
    parser.add_argument('-m', '--model',
                        help="Name of NN model to learn.",
                        default=None,
                        choices=GetModels())
    parser.add_argument("--optimizer","--opt",
                        help="optimizer to use with learning",
                        default="adam")
    parser.add_argument("--clip_weights",
                        help="clip the weights to [-value to +value] (0 is no clipping)",
                        type=float,
                        default=0.01),
    parser.add_argument("-z", "--zdim", "--noise_dim",
                        help="size of action parameterization",
                        type=int,
                        default=1)
    parser.add_argument("-D", "--debug_model", "--dm", "--debug",
                        help="Run a short script to debug the current model.",
                        action="store_true")
    parser.add_argument("--clipnorm",
                        help="Clip norm of gradients to this value to " + \
                              "prevent exploding gradients.",
                        default=100)
    parser.add_argument("--load_model", "--lm",
                        help="Load model from file for tests.",
                        action="store_true")
    parser.add_argument("--show_iter", "--si",
                        help="Show output images from model training" + \
                             " every N iterations.",
                        default=0,
                        type=int)
    parser.add_argument("--pretrain_iter", "--pi",
                        help="Number of iterations of pretraining to run" + \
                              ", in particular for training GAN" + \
                              " discriminators.",
                        default=0,
                        type=int)
    parser.add_argument("--load_pretrained_weights", "--lpw",
                        help="Load pretrained weights when training more"
                             " complex models. Will usually fail gracefully"
                             " if weights cannot be found. (GAN OPTION)",
                        action="store_true")
    parser.add_argument("--cpu",
                        help="Run in CPU-only mode, even if GPUs are" + \
                             " available.",
                        action="store_true",)
    parser.add_argument('--seed',
                        help="Seed used for running experiments.",
                        type=int)
    parser.add_argument('--profile',
                        help='Run cProfile on agent',
                        action="store_true")
    parser.add_argument('--features',
                        help="Specify feature function",
                        default="multi",
                        choices=GetAvailableFeatures())
    parser.add_argument('--steps_per_epoch',
                        help="Steps per epoch (used with the generator-" + \
                              "based version of the fit tool",
                        default=300,
                        type=int)
    parser.add_argument("--upsampling",
                        help="set upsampling definition",
                        choices=UpsamplingOptions(),
                        default="conv_transpose")
    parser.add_argument("--hypothesis_dropout",
                        help="dropout in hypothesis decoder",
                        default=True,
                        type=bool)
    parser.add_argument("--dropout_rate", "--dr",
                        help="Dropout rate to use",
                        type=float,
                        default=0.5)
    parser.add_argument("--enc_loss",
                        help="Add encoder loss",
                        action="store_true")
    parser.add_argument("--use_noise",
                        help="use random noise to sample distributions",
                        action='store_true',
                        default=False)
    parser.add_argument("--skip_connections", "--sc",
                        help="use skip connections to generate better outputs",
                        type=int,
                        default=1)
    parser.add_argument("--use_ssm", "--ssm",
                        help="use spatial softmax to compute global information",
                        type=int,
                        default=1)
    parser.add_argument("--decoder_dropout_rate", "--ddr",
                        help="specify a separate dropout for the model decoder",
                        #type=float,
                        default=None)
    parser.add_argument("--success_only",
                        help="only train on positive examples",
                        action="store_true")
    parser.add_argument("--loss",
                        help="Loss for state variables: MSE, MAE, or log(cosh).",
                        choices=["mse","mae","logcosh"],
                        default="mae")
    parser.add_argument("--gan_method",
                        help="Whether to train with GAN or no GAN",
                        dest='gan_method',
                        choices=["gan", "mae", "desc"],
                        default="gan")
    parser.add_argument("--no_save_model",
                        help="Should we save to the model file",
                        default=True,
                        dest='save_model',
                        action='store_false')
    parser.add_argument("--retrain",
                        help="Retrain sub-models",
                        action="store_true")
    parser.add_argument("--submodel",
                        help="Specific part of the planing model to train",
                        choices=GetSubmodelOptions(),
                        default="all")
    parser.add_argument("--use_batchnorm",
                        help="Use batchnorm (defaults to false; many models"
                              "do not use this parameter.",
                        type=int,
                        default=1)
    parser.add_argument("--option_num",
                        help="Choose an option to learn for the multi-policy hierarchical model",
                        type=int,
                        default=None)
    parser.add_argument("--gpu_fraction",
                        help="portion of the gpu to allocate for this job",
                        type=float,
                        default=1.)
    parser.add_argument("--preload",
                        help="preload all files into RAM", default=False,
                        action='store_true')
    parser.add_argument("--wasserstein",
                        help="Use weisserstein gan loss. Sets clip_weights to 0.01",
                        default=False,
                        dest='use_wasserstein',
                        action='store_true')
    parser.add_argument("--validate",
                        help="Validation mode.",
                        action="store_true")
    parser.add_argument("--no_disc",
                        help="Disable discriminator usage with images",
                        action="store_true")
    parser.add_argument("--unique_id",
                        help="Unique id to differentiate status file",
                        default="")
    parser.add_argument("--dense_transform",
                        help="Use dense layer for trasform",
                        default=False,
                        action='store_true')
    return parser

def GetSubmodelOptions():
    return ["q", "value", "actor", "pose", "next"]

def UpsamplingOptions():
    return [None,"upsampling","conv_transpose","bilinear"]


def ParseModelArgs():
    parser = argparse.ArgumentParser(add_help=True,
                                     parents=[GetModelParser()],
                                     description=_desc, epilog=_epilog)
    return vars(parser.parse_args())

def GetVisualizeParser():
    '''
    Get the set of arguments for showing data information.
    '''
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data_file", "-d",
                        help="file",
                        default="data.npz")
    parser.add_argument("--low", "-l",
                        help="Low index for images",
                        default=0,
                        type=int)
    parser.add_argument("--high", "-h",
                        help="High index for images",
                        default=10,
                        type=int)
    parser.add_argument("--comparison", "-c",
                        help="field to compare to input image",
                        default="goal_features",)
    parser.add_argument("--num_sets", "-n",
                        default=10)
    parser.add_argument("--visualization_mode",
                        choices=["train","test","sequence"],
                        default="train",
                        help="choose whether to debug train or test images")
    return parser

def ParseVisualizeArgs():
    _visualize_desc = "Visualize image data."
    _visualize_epilog = ""
    parser = argparse.ArgumentParser(add_help=True,
                                     parents=[GetVisualizeParser(),GetModelParser()],
                                     description=_visualize_desc,
                                     epilog=_visualize_epilog)
    return vars(parser.parse_args())
