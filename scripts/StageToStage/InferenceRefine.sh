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

# ----------------------Prepare for refine loop-----------------------------------
NUM_REFINE=1
PREV_JSON="${InitOutDir}/Init_${GENFILE}"
Init_file="${InitOutDir}/Init_${GENFILE}"
for ITER in $(seq 1 ${NUM_REFINE}); do
  echo "========== REFINE ROUND ${ITER} =========="

  REFINEDIR="baseline/results/$SaveDir/${RetrievalModel}/top${k}/${model_name}/Refine${ITER}"
  mkdir -p "${REFINEDIR}"
  python -m utils.GetPassedData \
    --input_file "${PREV_JSON}" \
    --mode "buggy" \
    --output_file "${REFINEDIR}/Error_${GENFILE}"

  QUERY_FILE="${REFINEDIR}/Error_${GENFILE}"
  RETRIEVAL_FILE="dataset/Filtered_pair/code1_Added_testScode_pairs/ReDiff_Exec_test_processed_pair.json"
  OUTPUT_FILE="${REFINEDIR}/ReRetrieval_${mode}.json"
  CUDA_VISIBLE_DEVICES=0 python -m VectorRetrieval.VectorRetrievalSecondStage \
    --query_file "${QUERY_FILE}" \
    --retrieval_file "${RETRIEVAL_FILE}" \
    --mode "${mode}" \
    --model_type "qwen_vllm" \
    --topk "${k}" \
    --output_file "${OUTPUT_FILE}" \
    --gpus "0"

  cmd="python -m generation.InferencePipeline \
    --config generation/config_file/inferenceConfig.yaml \
    --model /data/LLMs/$model_name \
    --data_path_dir $OUTPUT_FILE \
    --language $language \
    --save_file_path $REFINEDIR/Refine_${mode}.json \
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

  ExecPath="baseline/results/$SaveDir/${RetrievalModel}/EVAL/top${k}/${model_name}/Refine${ITER}/Execution"

  python -m Eval.Eval_Code_Generation-Mprocess \
      --EvalOject_Path "${REFINEDIR}/Refine_${mode}.json" \
      --Write_prefix_url "${ExecPath}/" \
      --CODE_KEY "code_content"

  FinalOutDir="baseline/results/$SaveDir/${RetrievalModel}/EVAL/top${k}/${model_name}/Refine${ITER}/EvaluateDesc"

  python -m Eval.Evaluate_DescriptionsRetry \
    --input_file "${ExecPath}/Exec_Refine_${mode}.json" \
    --output_dir "${FinalOutDir}" \
    --output_file "Refine_${GENFILE}" \
    --model "${EVAL_MODEL}" \
    --num_threads "${EVAL_NUM_THREADS}"

#----------------------Integration results-----------------------------------
  python -m utils.GetFinalData \
    --Init_file "$Init_file"\
    --Refine_file "${FinalOutDir}/Refine_${GENFILE}"\
    --output_file "${FinalOutDir}/Final_Res_${mode}.json"
    
  Init_file="${FinalOutDir}/Final_Res_${mode}.json"

  # Prepare input for the next round of iteration
  PREV_JSON="${FinalOutDir}/Final_Res_${mode}.json"
done

