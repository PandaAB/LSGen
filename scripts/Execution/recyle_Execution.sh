#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 <upcont>"
  exit 1
fi

UPCONT=$1
PATTERN="dev" 
CHECKPOINT=1200
SAVE_STEPS=100
FILE_NAME="DPOP_Fix_ND3V1-GEN" 
FILE_dir="DpoWeight"
export NCCL_P2P_DISABLE=1
export CUDA_LAUNCH_BLOCKING=1
export TORCH_USE_CUDA_DSA=1

while [ $CHECKPOINT -le $UPCONT ]
do
  echo "Running Execution eval for checkpoint $CHECKPOINT"
  python -m Eval.Eval_Code_Generation-Mprocess \
    --EvalOject_Path "./predict_dir/$FILE_dir/$FILE_NAME/$PATTERN-checkpoint-$CHECKPOINT.json"\
    --Write_prefix_url "./predict_evalResult_dir/$FILE_NAME/"\


  if [ $? -ne 0 ]; then
    echo "Error running eval for checkpoint $CHECKPOINT. Exiting."
    exit 1
  fi

  CHECKPOINT=$((CHECKPOINT + SAVE_STEPS))
done

echo "All evaluations completed."
