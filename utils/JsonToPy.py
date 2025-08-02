import json


def load_json(json_file_path):
    """read json file"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def json_to_python(Retrievaled_file_path, database_path, output_python_file_path, submission1_id = None):
    """Convert json to python"""
    data1 = load_json(Retrievaled_file_path)
    data2 = load_json(database_path)

    data1_dict = {}
    data2_dict = {}
    for each in data1:
        data1_dict[each["submission1_id"]] = each
    for each in data2:
        data2_dict[each["submission1_id"]] = each
    
    
    code1 = data1_dict[submission1_id]["code1"]
    code2 = data1_dict[submission1_id]["code2"]
    code3 = data1_dict[submission1_id]["diff_content"]

    code1_path = output_python_file_path + "/" + "code1.py"
    code2_path = output_python_file_path + "/" + "code2.py"
    code3_path = output_python_file_path + "/" + "diff_code1.py"

    path = [code1_path, code2_path, code3_path]
    code = [code1, code2, code3]

    for i in range(len(path)):
        with open(path[i], 'w', encoding='utf-8') as f_write:
                f_write.write(code[i])

    for i in range(len(data1_dict[submission1_id]["top_k_results"])):
        sb = data1_dict[submission1_id]["top_k_results"][i]['RetrievalSubmission1_id']
        RE_error_code = data2_dict[sb]['code1']
        print(sb)
        RE_code = data2_dict[sb]['code2']
        RE_diff = data2_dict[sb]['diff_code']

        RE_error_code_path = output_python_file_path + "/" + "Top" + str(i) + "RE_error_code.py"
        RE_code_path = output_python_file_path + "/" + "Top" + str(i) + "RE_code.py"
        RE_diff_path = output_python_file_path + "/" + "Top" + str(i) +"RE_diff.py"
        p = [RE_error_code_path, RE_code_path, RE_diff_path]
        c = [RE_error_code, RE_code, RE_diff]
        for i in range(len(p)):
            with open(p[i], 'w', encoding='utf-8') as f_write:
                f_write.write(c[i])

import os
def test(json_path, out_dir, PID):
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    data = load_json(json_path)
    for each in data:
        if each["problem_id"] == PID:
            t = out_dir+"/"+each["submission1_id"]
            os.mkdir(t)
            code1 = each["code1"]
            code2 = each["code2"]
            code3 = each["diff_code"]
            code1_path = t + "/" + "code1.py"
            code2_path = t + "/" + "code2.py"
            code3_path = t + "/" + "diff_code1.py"
            path = [code1_path, code2_path, code3_path]
            code = [code1, code2, code3]
            for i in range(len(path)):
                with open(path[i], 'w', encoding='utf-8') as f_write:
                    f_write.write(code[i])


if __name__ == "__main__":
    weight = "1011"
    Retrievaled_file_path = f"dataset/RetrievaledData/Retrievaled_{weight}_devTopk.json"
    database_path = "dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_dev_processed_pair.json"
    output_python_file_path = "dataset/RetrievaledData/temp"
    submission1_id = "s763982952"
    json_to_python(Retrievaled_file_path, database_path, output_python_file_path,submission1_id)

    # test("dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_dev_processed_pair.json", "dataset/RetrievaledData/temp/test", "p02419")


