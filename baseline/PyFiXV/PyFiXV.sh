model="claude-sonnet-4-20250514"
k=5

FirstStageToDir="baseline/results/StageToStage/PyFiXV/FirstStage/${model}"
FirstStageSaveFile="FirstRes.json"

python -m baseline.PyFiXV.PyFiXVFirst \
  --model "$model" \
  --test_dataset_file "data/ALL/origin_dataset_407.json" \
  --to_dir "${FirstStageToDir}" \
  --save_file_name "$FirstStageSaveFile"


RETRIEVAL_FILE="dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_test_processed_pair.json"
OUTPUT_FILE="baseline/PyFiXV/middle_output/RetrievalPyFiXV.json"
TOPK=5

python -m baseline.PyFiXV.LevenshteinDistence \
  --query_file "${FirstStageToDir}/${FirstStageSaveFile}" \
  --retrieval_file "$RETRIEVAL_FILE" \
  --topk "$TOPK" \
  --output_file "$OUTPUT_FILE"

python -m ProcessData.Get_Bug_Description.GetBugDescription \
    --test_dataset_file "$OUTPUT_FILE"\
    --retrieval_data_file "dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_test_processed_pair.json" \
    --to_dir "baseline/PyFiXV/middle_output"\
    --save_file_name "FirstAddDesc.json"

SecondStageToDir="baseline/results/StageToStage/PyFiXV/SecondStage/top$k/${model}"
SecondStageSaveFile="SecondRes_1.json"

python -m baseline.PyFiXV.PyFiXVSecond \
  --model "$model" \
  --test_dataset_file "baseline/PyFiXV/middle_output/FirstAddDesc.json" \
  --to_dir "${SecondStageToDir}" \
  --save_file_name "$SecondStageSaveFile"\
  --topk "${k}"\
  --use_ref

ExecutionPath="baseline/results/StageToStage/PyFiXV/EVAL/top$k/${model}/Execution"

python -m Eval.Eval_Code_Generation-Mprocess \
    --EvalOject_Path "./${SecondStageToDir}/${SecondStageSaveFile}" \
    --Write_prefix_url "./${ExecutionPath}/" \
    --CODE_KEY "code_content"

EVAL_MODEL="gpt-4o-mini-ca"
NUM_THREADS=16
FinalOutDir="baseline/results/StageToStage/PyFiXV/EVAL/top$k/${model}/EvaluateDesc"

python -m Eval.Evaluate_DescriptionsRetry \
  --input_file "${ExecutionPath}/Exec_${SecondStageSaveFile}" \
  --output_dir "${FinalOutDir}" \
  --output_file "Final_${SecondStageSaveFile}" \
  --model "$EVAL_MODEL" \
  --num_threads "$NUM_THREADS"

python -m baseline.calc_results \
    --json_file "./${FinalOutDir}/Final_${SecondStageSaveFile}"