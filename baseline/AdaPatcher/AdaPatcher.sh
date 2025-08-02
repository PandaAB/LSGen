MODEL="gpt-4o"
mode="AdaPatcher"

INPUTFILE="data/ALL/origin_dataset_407.json"
GENDIR="baseline/results/StageToStage/${mode}/$MODEL"
FIRST_GENFILE="First_${mode}.json"

python -m baseline.AdaPatcher.FirstStage \
    --problem_description_file "./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json"\
    --test_dataset_file "$INPUTFILE"\
    --model "$MODEL"\
    --to_dir "$GENDIR"\
    --save_file_name "$FIRST_GENFILE"\

SECOND_GENFILE="Second_${mode}.json"
python -m baseline.AdaPatcher.SecondStage \
    --problem_description_file "./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json"\
    --test_dataset_file "$GENDIR/$FIRST_GENFILE"\
    --model "$MODEL"\
    --to_dir "$GENDIR"\
    --save_file_name "$SECOND_GENFILE"\

ExecutionPath="baseline/results/StageToStage/AdaPatcher/EVAL/${MODEL}/Execution"

python -m Eval.Eval_Code_Generation-Mprocess \
    --EvalOject_Path "./${GENDIR}/${SECOND_GENFILE}" \
    --Write_prefix_url "./${ExecutionPath}/" \
    --CODE_KEY "code_content"

EVAL_MODEL="gpt-4o-mini-ca"
NUM_THREADS=10
FinalOutDir="baseline/results/StageToStage/AdaPatcher/EVAL/${MODEL}/EvaluateDesc"

python -m Eval.Evaluate_DescriptionsRetry \
  --input_file "${ExecutionPath}/Exec_${SECOND_GENFILE}" \
  --output_dir "${FinalOutDir}" \
  --output_file "Final_${mode}.json" \
  --model "$EVAL_MODEL" \
  --num_threads "$NUM_THREADS"

python -m baseline.calc_results \
    --json_file "./${FinalOutDir}/Final_${mode}.json" \


