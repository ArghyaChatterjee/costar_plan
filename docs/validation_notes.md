

# Some Validation Notes

## Data for Stack Task

Data set was created with an old version of pybullet, sort of unstable:
```
sudo -H pip install pybullet==1.2.2 -I
```

Command to get the data set:
```
./commands/collect_stack1_goals.sh gui_start
```

## Training/Target-wise Error

Basically you can get away with just predicting based on the successful
examples.

```
rosrun costar_models ctp_validate --data_file rpy.npz --model predictor
  -e 100 --features multi --batch_size 24  --optimizer adam --lr 0.001 \
  --upsampling conv_transpose --use_noise true --noise_dim 32 \
  --steps_per_epoch 300 \
  --decoder_dropout 0.25 --hypothesis_dropout true --dropout_rate 0.125 \
  --skip_connections 0 \
  --success_only \
  --model_directory \
  ~/.costar/MODEL_GOOD_NO_SKIP
```


### Validation: No Noise

```
```

## Keypoints

And the other command:

```
 rosrun costar_models ctp_keypoints --data_file rpy.npz --model predictor -e 1000 --features multi --batch_size 24  --optimizer adam --lr 0.001 --upsampling conv_transpose --use_noise true --noise_dim 32  --steps_per_epoch 300   --decoder_dropout 0.25 --hypothesis_dropout true --dropout_rate 0.125 --skip_connections 1 --success_only --model_directory ~/.costar/MODEL_RESULTS_GOOD
```


## Execution

```
rosrun costar_bullet gui_start --agent nn_planner \
  --task stack1  \
  --model predictor \
  -e 1000 \
  --features multi \
  --batch_size 8  \
  --optimizer adam \
  --lr 0.001 \
  --upsampling conv_transpose \
  --use_noise true \
  --noise_dim 8  \
  --steps_per_epoch 300   \
  --decoder_dropout 0.25 \
  --hypothesis_dropout true \
  --dropout_rate 0.125 \
  --skip_connections 1  \
  --model_directory ~/.costar/models \
  --seed 0
```

Or with the other sort of model:
```
rosrun costar_bullet gui_start \
  --agent nn_planner \
  --task stack1  \
  --model predictor \
  -e 1000 \
  --features multi \
  --batch_size 8  \
  --optimizer adam \
  --lr 0.001 \
  --upsampling conv_transpose \
  --use_noise true \
  --noise_dim 32  \
  --steps_per_epoch 300   \
  --decoder_dropout 0.25 \
  --hypothesis_dropout true \
  --dropout_rate 0.125 \
  --skip_connections 1 \
  --success_only \
  --model_directory ~/.costar/MODEL_RESULTS_GOOD \
  --seed 0
```
