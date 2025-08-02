# Description of scripts
- `get_pairs.sh` is used to obtain pairs of submission records from the raw data.
- `get_filtered_pairs.sh` is used to filter the pairs obtained above.
    * Filters out entries with the error type "Wrong Answer".
    * Sets a retention rate threshold and selects entries with a retention rate greater than a certain value.
    * If the parameter `mode` is set to `test`, a threshold for the number of lines will be added.
    * Each error record's `submission_id` will only appear once.
    * If `EXEC_EVAL` is set to true, the evaluation machine will be called:
        - First, `code2` will be evaluated on the filtered data, and entries where `code2` does not get a full score will be filtered out.
        - Then, `code1` will be evaluated on the processed data to obtain the results.