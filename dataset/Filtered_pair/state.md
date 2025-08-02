# File Description
- The `ALL_pairs` folder stores pairs of incorrect and correct codes with the same `user_id` in chronological order, filtered from the original dataset. (No threshold processing is performed on consistency or line count, and error types are not distinguished; i.e., Wrong Answer, TLE, and other errors are all included.)
- The `Processed_pair` folder contains further filtered results from ALL_pairs:
    * Only entries with the error type Wrong Answer are selected
    * A retention rate threshold is set, and only entries with a retention rate greater than a certain value are selected
    * If the parameter `mode` is set to `test`, a line count threshold will be added
    * Each error record's `submission_id` appears only once
- The `code2_Added_testScore_pairs` folder contains results where the correct code (`code2`) has been evaluated by the test machine, with the attributes `code_test_status`, `code_test_score`, and `TotalScore` added
- The `code1_Added_testScore_pairs` folder contains results where the incorrect code (`code1`) has been evaluated by the test machine, with the attributes `code_test_status`, `code_test_score`, and `TotalScore` added