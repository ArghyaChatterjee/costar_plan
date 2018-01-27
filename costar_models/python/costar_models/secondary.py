from keras.losses import binary_crossentropy
from keras.models import Model, Sequential
from keras.optimizers import Adam
from matplotlib import pyplot as plt

from .callbacks import *
from .sampler2 import *
from .data_utils import GetNextGoal, ToOneHot2D
from .multi import *


class Secondary(PredictionSampler2):
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
        super(Secondary, self).__init__(*args, **kwargs)
        self.PredictorCb = None
        self.load_training_model = False

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
        label_in = Input((1,))
        ins = [img0_in, img_in, arm_in, gripper_in]

        if self.skip_connections:
            encoder = self._makeImageEncoder2(img_shape)
            decoder = self._makeImageDecoder2(self.hidden_shape)
        else:
            encoder = self._makeImageEncoder(img_shape)
            decoder = self._makeImageDecoder(self.hidden_shape)

        LoadEncoderWeights(self, encoder, decoder)
        #image_discriminator = LoadGoalClassifierWeights(self,
        #        make_classifier_fn=MakeImageClassifier,
        #        img_shape=img_shape)
        tform = self._makeTransform()
        LoadTransformWeights(self, tform)

        # =====================================================================
        # Load the arm and gripper representation
        if self.skip_connections:
            h, s32, s16, s8 = encoder([img0_in, img_in])
        else:
            h = encoder([img_in])
            h0 = encoder(img0_in)

        next_option_in = Input((1,), name="next_option_in")
        next_option_in2 = Input((1,), name="next_option_in2")
        ins += [next_option_in, next_option_in2]
        y = OneHot(self.num_options)(next_option_in)
        y = Flatten()(y)

        actor = None
        if self.submodel == "value":
            model = GetValueModel(h, self.num_options, 64,
                    self.decoder_dropout_rate)
            model.compile(loss="mae", optimizer=self.getOptimizer())
            self.value_model = model
            outs = model([h0, h])
            loss = "binary_crossentropy"
            metrics=["accuracy"]
        elif self.submodel == "next":
            model = GetNextModel(h, self.num_options, 128,
                    self.decoder_dropout_rate)
            model.compile(loss="mae", optimizer=self.getOptimizer())
            outs = model([h0,h,label_in])
            self.next_model = model
            loss = "binary_crossentropy"
            metrics=["accuracy"]
        elif self.submodel == "actor":
            actor = GetActorModel(h, self.num_options, arm_size, gripper_size,
                    self.decoder_dropout_rate)
            actor.compile(loss="mae",optimizer=self.getOptimizer())
            model = actor
            outs = actor([h0, h, y])
            loss = self.loss
            metrics=[]
        elif self.submodel == "pose":
            model = GetPoseModel(h, self.num_options, arm_size, gripper_size,
                    self.decoder_dropout_rate)
            model.compile(loss="mae",optimizer=self.getOptimizer())
            self.pose_model = model
            outs = model([h0, h, y, arm_in, gripper_in])
            loss = self.loss
            metrics=[]

        model.summary()
        # =====================================================================
        train_predictor = Model(ins + [label_in], outs)
        train_predictor.compile(loss=loss,
                metrics=metrics,
                optimizer=self.getOptimizer())
        return None, train_predictor, actor, ins, h

    def _getData(self, *args, **kwargs):
        features, targets = GetAllMultiData(self.num_options, *args, **kwargs)
        [I, q, g, oin, label, q_target, g_target,] = features
        tt, o1, v, qa, ga, I_target = targets
        I_target2, o2 = GetNextGoal(I_target, o1)
        I0 = I[0,:,:,:]
        length = I.shape[0]
        I0 = np.tile(np.expand_dims(I0,axis=0),[length,1,1,1]) 
        oin_1h = np.squeeze(ToOneHot2D(oin, self.num_options))
        o1_1h = np.squeeze(ToOneHot2D(o1, self.num_options))
        o2_1h = np.squeeze(ToOneHot2D(o2, self.num_options))
        qa = np.squeeze(qa)
        ga = np.squeeze(ga)
        o1_1h = np.squeeze(ToOneHot2D(o1, self.num_options))
        if self.submodel == "value":
            outs = [v]
        elif self.submodel == "next":
            outs = [o1_1h]
        elif self.submodel == "actor":
            outs = [qa, ga]
        elif self.submodel == "pose":
            outs = [q_target, g_target]
        return ([I0, I, q, g, o1, o2, oin], outs)
