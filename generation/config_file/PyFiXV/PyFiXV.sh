export CUDA_VISIBLE_DEVICES=0,5
export NCCL_P2P_DISABLE=1
tp_size=2
model_name="CodeLlama-7b-Instruct-hf"
save_name="$model_name"
language="python"
without_context=false

RetrievalModel="PyFiXV"
prompt_mode="PyFiXVFirst"
RefTOPK=5

data_path_dir="data/ALL/origin_dataset_407.json"
save_file_dir="baseline/results/StageToStage/${RetrievalModel}/FirstStage/$model_name"
save_file_name="First_PyFiXV.json"
save_file_path="$save_file_dir/$save_file_name"

# FirstStage
cmd="python -m generation.config_file.PyFiXV.PyFiXVFirst \
    --config generation/config_file/PyFiXV/PyFiXVFirst.yaml \
    --model /data/LLMs/$model_name \
    --data_path_dir $data_path_dir \
    --language $language \
    --save_file_path $save_file_path \
    --dtype float16 \
    --dp_size 1 \
    --tp_size $tp_size \
    --gpu_memory_utilization 0.9 \
    --temperature 0.2 \
    --prompt_mode $prompt_mode"

if [ "$without_context" = true ]; then
    cmd="$cmd --without_context $without_context"
fi

# eval $cmd

RETRIEVAL_FILE="dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_test_processed_pair.json"
OUTPUT_FILE="baseline/results/StageToStage/${RetrievalModel}/FirstStage/$model_name/middle_output/Top${RefTOPK}_RetrievalPyFiXV.json"


python -m baseline.PyFiXV.LevenshteinDistence \
  --query_file "$save_file_path" \
  --retrieval_file "$RETRIEVAL_FILE" \
  --topk "$RefTOPK" \
  --output_file "$OUTPUT_FILE"

python -m ProcessData.Get_Bug_Description.GetBugDescription \
    --test_dataset_file "$OUTPUT_FILE"\
    --retrieval_data_file "dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_test_processed_pair.json" \
    --to_dir "baseline/results/StageToStage/${RetrievalModel}/FirstStage/$model_name/middle_output"\
    --save_file_name "Top${RefTOPK}_FirstAddDesc.json"

save_file_name="SecondRes.json"
save_file_dir="baseline/results/StageToStage/${RetrievalModel}/SecondStage/$model_name/top$RefTOPK"
Second_save_file_path="$save_file_dir/$save_file_name"
prompt_mode="PyFiXVSecond"

# SecondStage
cmd="python -m generation.config_file.PyFiXV.PyFiXVSecond \
    --config generation/config_file/PyFiXV/PyFiXVSecond.yaml \
    --model /data/LLMs/$model_name \
    --data_path_dir  baseline/results/StageToStage/${RetrievalModel}/FirstStage/$model_name/middle_output/Top${RefTOPK}_FirstAddDesc.json\
    --language $language \
    --save_file_path $Second_save_file_path \
    --dtype float16 \
    --dp_size 1 \
    --tp_size $tp_size \
    --gpu_memory_utilization 0.9 \
    --temperature 0.2 \
    --prompt_mode $prompt_mode \
    --batch_size 407"

if [ "$without_context" = true ]; then
    cmd="$cmd --without_context $without_context"
fi

eval $cmd

ExecutionPath="baseline/results/StageToStage/${RetrievalModel}/EVAL/top$RefTOPK/${model_name}/Execution"

python -m Eval.Eval_Code_Generation-Mprocess \
    --EvalOject_Path "./$Second_save_file_path" \
    --Write_prefix_url "./${ExecutionPath}/" \
    --CODE_KEY "code_content"

EVAL_MODEL="gpt-4o-mini-ca"
NUM_THREADS=16
FinalOutDir="baseline/results/StageToStage/${RetrievalModel}/EVAL/top$RefTOPK/${model_name}/EvaluateDesc"

python -m Eval.Evaluate_DescriptionsRetry \
  --input_file "${ExecutionPath}/Exec_${save_file_name}" \
  --output_dir "${FinalOutDir}" \
  --output_file "Final_${save_file_name}" \
  --model "$EVAL_MODEL" \
  --num_threads "$NUM_THREADS"

python -m baseline.calc_results \
    --json_file "./${FinalOutDir}/Final_${save_file_name}"