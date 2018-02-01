#!/bin/bash -l
#SBATCH --job-name=husky
#SBATCH --time=0-48:0:0
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --mem=8G
#SBATCH --mail-type=end
#SBATCH --mail-user=cpaxton3@jhu.edu


echo "Running $@ on $SLURMD_NODENAME ..."

module load tensorflow/cuda-8.0/r1.3 

export DATASET="husky_data"
export train_discriminator=false
export train_discriminator2=true
export train_image_encoder=false
export train_gans=false
export train_encoder_gan=true
export learning_rate=$1
export dropout=$2
export optimizer=$3
export noise_dim=$4
export loss=$5
export retrain=$6
export use_disc=$7
#export MODELDIR="$HOME/.costar/husky_$learning_rate$optimizer$dropout$noise_dim$loss"
export MODELROOT="$HOME/.costar"
export SUBDIR="husky_$learning_rate$optimizer$dropout$noise_dim$loss"

retrain_cmd=""
if $retrain
then
  retrain_cmd="--retrain"
  SUBDIR=${SUBDIR}_retrain
fi

use_disc_cmd=""
if [[ ! $use_disc ]]
then
  use_disc_cmd="--no_disc"
  SUBDIR=${SUBDIR}_nodisc
fi

export MODELDIR="$MODELROOT/$SUBDIR"
mkdir $MODELDIR
touch $MODELDIR/$SLURM_JOB_ID

if [[ $train_discriminator && $use_disc ]]
then
  echo "Training discriminator 1"
  $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
    --features multi \
    -e 100 \
    --model discriminator \
    --data_file $HOME/work/$DATASET.npz \
    --features husky \
    --lr $learning_rate \
    --dropout_rate $dropout \
    --model_directory $MODELDIR/ \
    --optimizer $optimizer \
    --steps_per_epoch 500 \
    --noise_dim $noise_dim \
    --loss $loss \
    --batch_size 64
fi
if [[ $train_discriminator2 && $use_disc ]]
  echo "Training discriminator 2"
  $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
    --features multi \
    -e 10 \
    --model goal_discriminator \
    --data_file $HOME/work/$DATASET.npz \
    --lr $learning_rate \
    --features husky \
    --dropout_rate $dropout \
    --model_directory $MODELDIR/ \
    --optimizer $optimizer \
    --steps_per_epoch 500 \
    --noise_dim $noise_dim \
    --loss $loss \
    --batch_size 64
fi

if $train_image_encoder
then
  echo "Training encoder 1 $use_disc_cmd"
  $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
    --features multi \
    -e 100 \
    --model pretrain_image_encoder \
    --data_file $HOME/work/$DATASET.npz \
    --lr $learning_rate \
    --dropout_rate $dropout \
    --features husky \
    --model_directory $MODELDIR/ \
    --optimizer $optimizer \
    --steps_per_epoch 500 \
    --noise_dim $noise_dim \
    --loss $loss \
    --batch_size 64 $use_disc_cmd
fi

$HOME/costar_plan/costar_models/scripts/ctp_model_tool \
  --features multi \
  -e 100 \
  --model conditional_image \
  --data_file $HOME/work/$DATASET.npz \
  --features husky \
  --lr $learning_rate \
  --dropout_rate $dropout \
  --model_directory $MODELDIR/ \
  --optimizer $optimizer \
  --steps_per_epoch 500 \
  --loss $loss \
  --batch_size 64 $retrain_cmd $use_disc_cmd

