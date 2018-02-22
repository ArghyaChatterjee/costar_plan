from __future__ import print_function

import keras.backend as K
import keras.losses as losses
import keras.optimizers as optimizers
import numpy as np

from keras.callbacks import ModelCheckpoint
from keras.layers.advanced_activations import LeakyReLU
from keras.layers import Input, RepeatVector, Reshape
from keras.layers.embeddings import Embedding
from keras.layers.merge import Concatenate, Multiply
from keras.losses import binary_crossentropy
from keras.models import Model, Sequential
from keras.layers.pooling import GlobalAveragePooling2D
from keras.optimizers import Adam
from matplotlib import pyplot as plt

from .callbacks import *
from .pretrain_image_gan import *
from .planner import *

class ConditionalImageGan(PretrainImageGan):
    '''
    Version of the sampler that only produces results conditioned on a
    particular action; this version does not bother trying to learn a separate
    distribution for each possible state.

    This one generates:
      - image
      - arm command
      - gripper command
    '''

    def __init__(self, *args, **kwargs):
        '''
        As in the other models, we call super() to parse arguments from the
        command line and set things like our optimizer and learning rate.

        Parameters:
        -----------
        taskdef: definition of the problem used to create a task model
        '''
        super(ConditionalImageGan, self).__init__(*args, **kwargs)
        self.PredictorCb = ImageWithFirstCb
        self.rep_size = 256
        self.num_transforms = 3
        self.do_all = True
        self.save_encoder_decoder = self.retrain
        self.noise_iters = 2

    def _makePredictor(self, features):
        # =====================================================================
        # Create many different image decoders
        (images, arm, gripper) = features
        img_shape, image_size, arm_size, gripper_size = self._sizes(
                images,
                arm,
                gripper)

        # =====================================================================
        # Load the image decoders
        img_in = Input(img_shape,name="predictor_img_in")
        img0_in = Input(img_shape,name="predictor_img0_in")
        arm_in = Input((arm_size,))
        gripper_in = Input((gripper_size,))
        arm_gripper = Concatenate()([arm_in, gripper_in])
        label_in = Input((1,))
        next_option_in = Input((1,), name="next_option_in")
        next_option2_in = Input((1,), name="next_option2_in")
        ins = [img0_in, img_in, next_option_in, next_option2_in]

        encoder = self._makeImageEncoder(img_shape, perm_drop=True)
        decoder = self._makeImageDecoder(self.hidden_shape, perm_drop=True)

        LoadEncoderWeights(self, encoder, decoder, gan=True)

        # create input for controlling noise output if that's what we decide
        # that we want to do
        if self.use_noise:
            z1 = Input((self.noise_dim,), name="z1_in")
            z2 = Input((self.noise_dim,), name="z2_in")
            ins += [z1, z2]

        h = encoder([img_in])
        h0 = encoder(img0_in)

        # =====================================================================
        # Actually get the right outputs
        y = Flatten()(OneHot(self.num_options)(next_option_in))
        y2 = Flatten()(OneHot(self.num_options)(next_option2_in))
        x = h
        tform = self._makeTransform()
        l = [h0, h, y, z1] if self.use_noise else [h0, h, y]
        x = tform(l)
        l = [h0, x, y2, z2] if self.use_noise else [h0, x, y2]
        x2 = tform(l)
        image_out, image_out2 = decoder([x]), decoder([x2])

        # =====================================================================
        # Save
        self.transform_model = tform

        # =====================================================================
        # Make the discriminator
        image_discriminator = self._makeImageDiscriminator(img_shape)
        self.discriminator = image_discriminator

        image_discriminator.trainable = False
        is_fake = image_discriminator([
            img0_in, img_in,
            next_option_in, next_option2_in,
            image_out, image_out2])

        # =====================================================================
        # Create generator model to train
        lfn = self.loss
        predictor = Model(ins, [image_out, image_out2])
        predictor.compile(
                loss=[lfn, lfn], # ignored since we don't train G
                optimizer=self.getOptimizer())
        self.generator = predictor

        # =====================================================================
        # And adversarial model
        loss = wasserstein_loss if self.use_wasserstein else "binary_crossentropy"
        weights = [0.1, 0.1, 1.] if self.use_wasserstein else [100., 100., 1.]

        model = Model(ins, [image_out, image_out2, is_fake])
        model.compile(
                loss=['mae', 'mae', loss],
                loss_weights=weights,
                optimizer=self.getOptimizer())
        self.model = model

        self.discriminator.summary()
        self.model.summary()

        return predictor, model, model, ins, h

    def _getData(self, *args, **kwargs):
        features, targets = GetAllMultiData(self.num_options, *args, **kwargs)
        [I, q, g, oin, label, q_target, g_target,] = features
        tt, o1, v, qa, ga, I_target = targets

        # Create the next image including input image
        I0 = I[0,:,:,:]
        length = I.shape[0]
        I0 = np.tile(np.expand_dims(I0,axis=0),[length,1,1,1])

        # Extract the next goal
        I_target2, o2 = GetNextGoal(I_target, o1)
        return [I0, I, o1, o2], [ I_target, I_target2 ]

    def _makeImageDiscriminator(self, img_shape):
        '''
        create image-only encoder to extract keypoints from the scene.

        Params:
        -------
        img_shape: shape of the image to encode
        '''
        img0 = Input(img_shape,name="img0_encoder_in")
        img = Input(img_shape,name="img_encoder_in")
        img_goal = Input(img_shape,name="goal_encoder_in")
        img_goal2 = Input(img_shape,name="goal2_encoder_in")
        option = Input((1,),name="disc_options")
        option2 = Input((1,),name="disc2_options")
        ins = [img0, img, option, option2, img_goal, img_goal2]
        dr = self.dropout_rate

        # common arguments
        kwargs = { "dropout_rate" : dr,
                   "padding" : "same",
                   "lrelu" : True,
                   "bn" : False,
                   "perm_drop" : True,
                 }

        x0   = AddConv2D(img0,      64, [4,4], 1, **kwargs)
        xobs = AddConv2D(img,       64, [4,4], 1, **kwargs)
        xg1  = AddConv2D(img_goal,  64, [4,4], 1, **kwargs)
        xg2  = AddConv2D(img_goal2, 64, [4,4], 1, **kwargs)

        #x1 = Add()([x0, xobs, xg1])
        #x2 = Add()([x0, xg1, xg2])
        x1 = Add()([xobs, xg1])
        x2 = Add()([xg1, xg2])

        # -------------------------------------------------------------
        y = OneHot(self.num_options)(option)
        y = AddDense(y, 64, "lrelu", dr, perm_drop=True)
        x1 = TileOnto(x1, y, 64, (64,64), add=True)
        x1 = AddConv2D(x1, 64, [4,4], 2, **kwargs)

        # -------------------------------------------------------------
        y = OneHot(self.num_options)(option2)
        y = AddDense(y, 64, "lrelu", dr, perm_drop=True)
        x2 = TileOnto(x2, y, 64, (64,64), add=True)
        x2 = AddConv2D(x2, 64, [4,4], 2, **kwargs)

        #x = Concatenate()([x1, x2])
        x = x2
        x = AddConv2D(x, 128, [4,4], 2, **kwargs)
        x = AddConv2D(x, 256, [4,4], 2, **kwargs)

        if self.use_wasserstein:
            x = Flatten()(x)
            x = AddDense(x, 1, "linear", 0., output=True, bn=False)
        else:
            #x = AddConv2D(x, 1, [1,1], 1, 0., "same", activation="sigmoid",
            #    bn=False)
            #x = GlobalAveragePooling2D()(x)
            x = Flatten()(x)
            x = AddDense(x, 1, "sigmoid", 0., output=True, bn=False, perm_drop=True)

        discrim = Model(ins, x, name="image_discriminator")
        self.lr *= 2.
        loss = wasserstein_loss if self.use_wasserstein else "binary_crossentropy"
        discrim.compile(loss=loss, optimizer=self.getOptimizer())
        self.lr *= 0.5
        self.image_discriminator = discrim
        return discrim


