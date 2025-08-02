export CUDA_VISIBLE_DEVICES=1,7
export NCCL_P2P_DISABLE=1
tp_size=2
model_name="CodeLlama-7b-Instruct-hf"
language="python"
without_context=false

mode="code1+diff-code2"
RetrievalModel="AdaPatcher"
RetrievalDir="Qwen3-Embedding-0.6BData"
prompt_mode="AdaPatcherFirst"

data_path_dir="data/ALL/${RetrievalDir}/desc/desc_${mode}.json"
save_file_dir="baseline/results/StageToStage/${RetrievalModel}/$model_name"
save_file_name="First_AdaPatcher.json"
save_file_path="$save_file_dir/$save_file_name"

# FirstStage
cmd="python -m generation.config_file.AdaPatcher.AdaPatcherFirst \
    --config generation/config_file/AdaPatcher/AdaPatcherFirst.yaml \
    --model /data/LLMs/$model_name \
    --data_path_dir $data_path_dir \
    --language $language \
    --save_file_path $save_file_path \
    --dtype float16 \
    --dp_size 1 \
    --tp_size $tp_size \
    --gpu_memory_utilization 0.97 \
    --temperature 0.2 \
    --prompt_mode $prompt_mode"

if [ "$without_context" = true ]; then
    cmd="$cmd --without_context $without_context"
fi

# eval $cmd

save_file_name="Second_AdaPatcher.json"
Second_save_file_path="$save_file_dir/$save_file_name"
prompt_mode="AdaPatcherSecond"
# SecondStage
cmd="python -m generation.InferencePipeline \
    --config generation/config_file/inferenceConfig.yaml \
    --model /data/LLMs/$model_name \
    --data_path_dir $save_file_path \
    --language $language \
    --save_file_path $Second_save_file_path \
    --dtype float16 \
    --dp_size 1 \
    --tp_size $tp_size \
    --gpu_memory_utilization 0.97 \
    --temperature 0.2 \
    --prompt_mode $prompt_mode"

if [ "$without_context" = true ]; then
    cmd="$cmd --without_context $without_context"
fi

eval $cmd


ExecutionPath="baseline/results/StageToStage/${RetrievalModel}/EVAL/${model_name}/Execution"

python -m Eval.Eval_Code_Generation-Mprocess \
    --EvalOject_Path "./$Second_save_file_path" \
    --Write_prefix_url "./${ExecutionPath}/" \
    --CODE_KEY "code_content"

EVAL_MODEL="gpt-4o-mini-ca"
NUM_THREADS=16
FinalOutDir="baseline/results/StageToStage/${RetrievalModel}/EVAL/${model_name}/EvaluateDesc"

python -m Eval.Evaluate_DescriptionsRetry \
  --input_file "${ExecutionPath}/Exec_${save_file_name}" \
  --output_dir "${FinalOutDir}" \
  --output_file "Final_${save_file_name}" \
  --model "$EVAL_MODEL" \
  --num_threads "$NUM_THREADS"

python -m baseline.calc_results \
    --json_file "./${FinalOutDir}/Final_${save_file_name}"