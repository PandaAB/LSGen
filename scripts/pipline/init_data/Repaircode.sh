for i in {1..3}
do
    python -m ProcessData.create_data.RepairCode \
        --model "gpt-4o-ca" \
        --problem_description_file "./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json" \
        --test_dataset_file "dataset/test.json" \
        --to_dir "dataset/Init" \
        --save_file_name "repair_${i}.json"
done
