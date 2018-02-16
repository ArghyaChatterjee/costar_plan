#!/bin/bash -l
#SBATCH --job-name=ctpZ
#SBATCH --time=0-48:0:0
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --mem=8G
#SBATCH --mail-type=end
#SBATCH --mail-user=cpaxton3@jhu.edu


echo "Running $@ on $SLURMD_NODENAME ..."

export DATASET="ctp_dec"
export train_discriminator2=true
export train_image_encoder=true
export train_conditional_image=true
export train_policies=false

export learning_rate=$1
export dropout=$2
export optimizer=$3
export noise_dim=$4
export loss=$5
export retrain=$6
export use_disc=$7
#export MODELDIR="$HOME/.costar/stack_$learning_rate$optimizer$dropout$noise_dim$loss"
export MODELROOT="$HOME/.costar"
export SUBDIR="stack_$learning_rate$optimizer$dropout$noise_dim$loss"
export USE_BN=1

echo $1 $2 $3 $4 $5 $6 $7
echo "use disc = $use_disc"

# ----------------------------------
# Old versions
export train_multi_encoder=false
export train_conditional_sampler=false
export train_predictor=false

retrain_cmd=""
if $retrain
then
  echo "retrain models"
  retrain_cmd="--retrain"
  SUBDIR=${SUBDIR}_retrain
fi

use_disc_cmd=""
if ! $use_disc ; then
  use_disc_cmd="--no_disc"
  SUBDIR=${SUBDIR}_nodisc
fi

export MODELDIR="$MODELROOT/$SUBDIR"
mkdir $MODELDIR
touch $MODELDIR/$SLURM_JOB_ID

echo "Options are: $retrain_cmd $use_disc_cmd $1 $2 $3 $4 $5"
echo "Directory is $MODELDIR"
echo "Slurm job ID = $SLURM_JOB_ID"

export learning_rate_disc=0.001
export learning_rate_enc=0.001

if $train_discriminator2 && $use_disc ; then
  echo "Training discriminator 2"
  $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
    --features multi \
    -e 100 \
    --model goal_discriminator \
    --data_file $HOME/work/$DATASET.h5f \
    --lr $learning_rate_disc \
    --dropout_rate $dropout \
    --model_directory $MODELDIR/ \
    --optimizer $optimizer \
    --steps_per_epoch 500 \
    --noise_dim $noise_dim \
    --loss $loss \
    --use_batchnorm $USE_BN \
    --batch_size 64
fi

if $train_image_encoder
then
  echo "Training encoder 1"
  $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
    --features multi \
    -e 100 \
    --model pretrain_image_encoder \
    --data_file $HOME/work/$DATASET.h5f \
    --lr $learning_rate_enc \
    --dropout_rate $dropout \
    --model_directory $MODELDIR/ \
    --optimizer $optimizer \
    --steps_per_epoch 500 \
    --noise_dim $noise_dim \
    --use_batchnorm $USE_BN \
    --loss $loss \
    --batch_size 64 --no_disc
fi

if $train_conditional_image
then
  $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
    --features multi \
    -e 150 \
    --model conditional_image \
    --data_file $HOME/work/$DATASET.h5f \
    --lr $learning_rate \
    --dropout_rate $dropout \
    --model_directory $MODELDIR/ \
    --optimizer $optimizer \
    --steps_per_epoch 500 \
    --use_batchnorm $USE_BN \
    --loss $loss \
    --batch_size 64 $retrain_cmd $use_disc_cmd
fi

# ==============================================
# ==============================================
#  These are all old commands.
# ==============================================
# ==============================================

if $train_multi_encoder
then
  echo "Training encoder 2"
  $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
    --features multi \
    -e 100 \
    --model pretrain_sampler \
    --data_file $HOME/work/$DATASET.h5f \
    --lr $learning_rate \
    --dropout_rate $dropout \
    --model_directory $MODELDIR/ \
    --optimizer $optimizer \
    --steps_per_epoch 500 \
    --noise_dim $noise_dim \
    --loss $loss \
    --batch_size 64
fi

if $train_conditional_sampler
then
$HOME/costar_plan/costar_models/scripts/ctp_model_tool \
  --features multi \
  -e 100 \
  --model conditional_sampler2 \
  --data_file $HOME/work/$DATASET.h5f \
  --lr $learning_rate \
  --dropout_rate $dropout \
  --model_directory $MODELDIR/ \
  --optimizer $optimizer \
  --steps_per_epoch 500 \
  --loss $loss \
  --batch_size 64
fi

if $train_predictor
then
  $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
    --features multi \
    -e 100 \
    --model predictor \
    --data_file $HOME/work/$DATASET.h5f \
    --lr $learning_rate \
    --dropout_rate $dropout \
    --model_directory $MODELDIR/ \
    --optimizer $optimizer \
    --steps_per_epoch 500 \
    --loss $loss \
    --skip_connections 1 \
    --batch_size 64
fi


if $train_policies
then
  for opt in $(seq 0 36)
  do
    $HOME/costar_plan/costar_models/scripts/ctp_model_tool \
      --features multi \
      -e 100 \
      --model policy \
      --data_file $HOME/work/$DATASET.h5f \
      --lr $learning_rate \
      --dropout_rate $dropout \
      --model_directory $MODELDIR/ \
      --optimizer $optimizer \
      --steps_per_epoch 500 \
      --loss $loss \
      --option_num $opt \
      --skip_connections 1 \
      --success_only \
      --batch_size 64
    done
fi
