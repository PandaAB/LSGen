MODEL="claude-sonnet-4-20250514"
k=5
mode="code1-code2"
RetrievalModel="RetrievalMethod"
RetrievalDir="Qwen3-Embedding-0.6BData"
SaveDir="AblationStudy"

INPUTFILE="data/ALL/${RetrievalDir}/desc/desc_${mode}.json"
GENDIR="baseline/results/${SaveDir}/${RetrievalModel}/top${k}/${MODEL}/Init"
GENFILE="Res_${mode}.json"

EVAL_MODEL="gpt-4o-mini-ca"
EVAL_NUM_THREADS=16

#----------------------First Generate-----------------------------------
python -m Eval.RepairCodeAndExplainRetryDiff \
    --problem_description_file "./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json" \
    --test_dataset_file "${INPUTFILE}" \
    --model "${MODEL}" \
    --to_dir "${GENDIR}" \
    --save_file_name "${GENFILE}" \
    --topk "${k}"

ExecutionPath="baseline/results/${SaveDir}/${RetrievalModel}/EVAL/top${k}/${MODEL}/Init/Execution"

python -m Eval.Eval_Code_Generation-Mprocess \
    --EvalOject_Path "${GENDIR}/${GENFILE}" \
    --Write_prefix_url "${ExecutionPath}/" \
    --CODE_KEY "code_content"

InitOutDir="baseline/results/${SaveDir}/${RetrievalModel}/EVAL/top${k}/${MODEL}/Init/EvaluateDesc"

python -m Eval.Evaluate_DescriptionsRetry \
  --input_file "${ExecutionPath}/Exec_${GENFILE}" \
  --output_dir "${InitOutDir}" \
  --output_file "Init_${GENFILE}" \
  --model "${EVAL_MODEL}" \
  --num_threads "${EVAL_NUM_THREADS}"

#----------------------Prepare for refine loop-----------------------------------
# 从第一次 refine 开始迭代，NUM_REFINE 控制总轮数
NUM_REFINE=1
PREV_JSON="${InitOutDir}/Init_${GENFILE}"
Init_file="${InitOutDir}/Init_${GENFILE}"
for ITER in $(seq 1 ${NUM_REFINE}); do
  echo "========== REFINE ROUND ${ITER} =========="

  # 1. 筛选出未通过的样本
  REFINEDIR="baseline/results/${SaveDir}/${RetrievalModel}/top${k}/${MODEL}/Refine${ITER}"
  mkdir -p "${REFINEDIR}"
  python -m utils.GetPassedData \
    --input_file "${PREV_JSON}" \
    --mode "buggy" \
    --output_file "${REFINEDIR}/Error_${GENFILE}"

  # 2. 二阶段检索
  QUERY_FILE="${REFINEDIR}/Error_${GENFILE}"
  RETRIEVAL_FILE="dataset/Filtered_pair/code1_Added_testScode_pairs/ReDiff_Exec_test_processed_pair.json"
  OUTPUT_FILE="${REFINEDIR}/ReRetrieval_${mode}.json"
  CUDA_VISIBLE_DEVICES=1 python -m VectorRetrieval.VectorRetrievalSecondStage \
    --query_file "${QUERY_FILE}" \
    --retrieval_file "${RETRIEVAL_FILE}" \
    --mode "${mode}" \
    --model_type "qwen_vllm" \
    --topk "${k}" \
    --output_file "${OUTPUT_FILE}" \
    --gpus "0"

  # 3. 根据检索结果重新生成
  python -m Eval.DiffRef_Refine \
      --problem_description_file "./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json" \
      --test_dataset_file "${OUTPUT_FILE}" \
      --model "${MODEL}" \
      --to_dir "${REFINEDIR}" \
      --save_file_name "Refine_${mode}.json" \
      --topk "${k}"

  ExecPath="baseline/results/${SaveDir}/${RetrievalModel}/EVAL/top${k}/${MODEL}/Refine${ITER}/Execution"

  python -m Eval.Eval_Code_Generation-Mprocess \
      --EvalOject_Path "${REFINEDIR}/Refine_${mode}.json" \
      --Write_prefix_url "${ExecPath}/" \
      --CODE_KEY "code_content"

  FinalOutDir="baseline/results/${SaveDir}/${RetrievalModel}/EVAL/top${k}/${MODEL}/Refine${ITER}/EvaluateDesc"

  python -m Eval.Evaluate_DescriptionsRetry \
    --input_file "${ExecPath}/Exec_Refine_${mode}.json" \
    --output_dir "${FinalOutDir}" \
    --output_file "Refine_${GENFILE}" \
    --model "${EVAL_MODEL}" \
    --num_threads "${EVAL_NUM_THREADS}"

#----------------------整合结果-----------------------------------
  python -m utils.GetFinalData \
    --Init_file "$Init_file"\
    --Refine_file "${FinalOutDir}/Refine_${GENFILE}"\
    --output_file "${FinalOutDir}/Final_Res_${mode}.json"
    
  Init_file="${FinalOutDir}/Final_Res_${mode}.json"

  # 为下一轮迭代准备输入
  PREV_JSON="${FinalOutDir}/Final_Res_${mode}.json"
done