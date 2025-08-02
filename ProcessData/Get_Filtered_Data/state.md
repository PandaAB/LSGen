# File Description
- `get_pairs.py`: From the original dataset, filters out the error code and correct code of the same `user_id` in chronological order (this step does not set thresholds for retention rate or line count, nor does it distinguish error types, i.e., errors such as Wrong Answer, TLE, etc. are all included).
Startup script: `scripts/get_pairs.sh`
- `filter_submission_pairs.py`: Further filters the results obtained from the previous step.
    * Filters out entries with the error type "Wrong Answer".
    * Sets a retention rate threshold and selects entries with a retention rate greater than a certain value.
    * If the parameter `mode` is set to `test`, a threshold for the number of lines will be added.
    * Each error record's `submission_id` will only appear once.