mode="code1-code2"

python -m ProcessData.Get_Bug_Description.GetBugDescription \
    --test_dataset_file "data/ALL/Qwen3-Embedding-0.6BData/code1+diff-code2.json"\
    --retrieval_data_file "dataset/Filtered_pair/code1_Added_testScode_pairs/ReDiff_Exec_test_processed_pair.json" \
    --to_dir "data/ALL/Qwen3-Embedding-0.6BData/desc"\
    --save_file_name "desc_${mode}.json"