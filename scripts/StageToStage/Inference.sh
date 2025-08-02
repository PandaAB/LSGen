export CUDA_VISIBLE_DEVICES=1,7
export NCCL_P2P_DISABLE=1
model_name="Qwen2.5-Coder-7B-Instruct"
language="python"
without_context=false

k=5
mode="code1+diff-code2"
RetrievalModel="RetrievalMethod"
RetrievalDir="Qwen3-Embedding-0.6BData"
prompt_mode="CommentTextRefDiff"
SaveDir="StageToStage"

INPUTFILE="data/ALL/${RetrievalDir}/desc/desc_${mode}.json"
GENDIR="baseline/results/$SaveDir/${RetrievalModel}/top${k}/${model_name}/Init"
GENFILE="Res_${mode}.json"

EVAL_MODEL="gpt-4o-mini-ca"
EVAL_NUM_THREADS=16

#----------------------First Generate-----------------------------------
cmd="python -m generation.InferencePipeline \
    --config generation/config_file/inferenceConfig.yaml \
    --model /data/LLMs/$model_name \
    --data_path_dir $INPUTFILE \
    --language $language \
    --save_file_path $GENDIR/$GENFILE \
    --dtype float16 \
    --dp_size 1 \
    --tp_size 2 \
    --gpu_memory_utilization 0.9 \
    --temperature 0.2 \
    --prompt_mode $prompt_mode"

if [ "$without_context" = true ]; then
    cmd="$cmd --without_context $without_context"
fi

eval $cmd

ExecutionPath="baseline/results/$SaveDir/${RetrievalModel}/EVAL/top${k}/${model_name}/Init/Execution"

python -m Eval.Eval_Code_Generation-Mprocess \
    --EvalOject_Path "${GENDIR}/${GENFILE}" \
    --Write_prefix_url "${ExecutionPath}/" \
    --CODE_KEY "code_content"

InitOutDir="baseline/results/$SaveDir/${RetrievalModel}/EVAL/top${k}/${model_name}/Init/EvaluateDesc"

python -m Eval.Evaluate_DescriptionsRetry \
  --input_file "${ExecutionPath}/Exec_${GENFILE}" \
  --output_dir "${InitOutDir}" \
  --output_file "Init_${GENFILE}" \
  --model "${EVAL_MODEL}" \
  --num_threads "${EVAL_NUM_THREADS}"