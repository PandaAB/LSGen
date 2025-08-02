MODEL="gpt-4o-ca"
k=5
mode="code1+diff-code2"
RetrievalModel="CommentDiff"
RetrievalDir="Qwen3-Embedding-0.6BData"

INPUTFILE="data/ALL/${RetrievalDir}/desc/desc_${mode}.json"
GENDIR="baseline/results/StageToStage/${RetrievalModel}/top$k/$MODEL"
GENFILE="Res_${mode}.json"

python -m Eval.RepairCodeAndExplainRetryDiff \
    --problem_description_file "./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json"\
    --test_dataset_file "$INPUTFILE"\
    --model "$MODEL"\
    --to_dir "$GENDIR"\
    --save_file_name "$GENFILE"\
    --topk $k

ExecutionPath="baseline/results/StageToStage/${RetrievalModel}/EVAL/top$k/${MODEL}/Execution"

python -m Eval.Eval_Code_Generation-Mprocess \
    --EvalOject_Path "./${GENDIR}/${GENFILE}" \
    --Write_prefix_url "./${ExecutionPath}/" \
    --CODE_KEY "code_content"

EVAL_MODEL="gpt-4o-mini-ca"
NUM_THREADS=16
FinalOutDir="baseline/results/StageToStage/${RetrievalModel}/EVAL/top$k/${MODEL}/EvaluateDesc"

python -m Eval.Evaluate_DescriptionsRetry \
  --input_file "${ExecutionPath}/Exec_${GENFILE}" \
  --output_dir "${FinalOutDir}" \
  --output_file "Final_${GENFILE}" \
  --model "$EVAL_MODEL" \
  --num_threads "$NUM_THREADS"

python -m baseline.calc_results \
    --json_file "./${FinalOutDir}/Final_${GENFILE}"
