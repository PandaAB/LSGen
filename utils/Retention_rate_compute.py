import os
import json
import subprocess
import re
import argparse
from tqdm import tqdm

from utils.utils import save_data_to_json
from utils.remove_comments import remove_comments

def read_json(json_name):
    with open(json_name, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data
def read_python_code(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def remove_empty_lines(code):
    return '\n'.join(line for line in code.splitlines() if line.strip())

def save_python_file(code1, code2, save_dir, name1 = "code1.py", name2 = "code2.py"):
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # code1_filename = os.path.join(save_dir, f'code1.py')
    # code2_filename = os.path.join(save_dir, f'code2.py')
    code1_filename = os.path.join(save_dir, name1)
    code2_filename = os.path.join(save_dir, name2)
    
    with open(code1_filename, 'w') as code1_file:
        code1_file.write(code1)
        code1_file.write('\n')
    with open(code2_filename, 'w') as code2_file:
        code2_file.write(code2)
        code2_file.write('\n')
    return code1_filename, code2_filename

def save_temp_file(code1_file,code2_file,temp_dir, name1 = "code1.py", name2 = "code2.py"):

    code1 = read_python_code(code1_file)
    code2 = read_python_code(code2_file)

    code1 = remove_comments(code1)
    code2 = remove_comments(code2)

    # code1 = remove_empty_lines(code1)
    # code2 = remove_empty_lines(code2)

    # code1_filename = os.path.join(temp_dir, f'code1.py')
    # code2_filename = os.path.join(temp_dir, f'code2.py')
    code1_filename = os.path.join(temp_dir, name1)
    code2_filename = os.path.join(temp_dir, name2)

    # Write the content to the files
    with open(code1_filename, 'w') as code1_file:
        code1_file.write(code1)
        code1_file.write('\n')
    with open(code2_filename, 'w') as code2_file:
        code2_file.write(code2)
        code2_file.write('\n')
    
    #print(f'************Saved {submission1_id} code1 to {code1_filename}************')
    #print(f'************Saved {submission1_id} code2 to {code2_filename}************')

    return code1_filename, code2_filename

def process_diff_file(input_file, output_file, new_indicator="+", old_indicator="-"):

    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        added_line_written = False

        for _ in range(4):
            next(infile)

        for line in infile:
            if line.startswith("+++"):
                outfile.write(line)
                continue
            
            if line.startswith("@@"):
                continue
            
            if line.startswith(new_indicator):
                if not added_line_written:
                    # outfile.write(new_indicator + '\n')
                    outfile.write('<+>' + '\n')
                    added_line_written = True

            elif line.startswith(old_indicator):
                continue
            else:
                outfile.write(line)
                added_line_written = False

def add_empty_line_to_file(filename):
    with open(filename, 'a') as file:
        file.write('\n')

def remove_last_empty_line(file_path):
    try:
        with open(file_path, 'r+', encoding='utf-8') as file:
            lines = file.readlines()
            if not lines:
                print("The file is empty.")
                return
            
            if lines[-1].strip() == '':
                lines = lines[:-1]
            
            file.seek(0)
            file.truncate()
            file.writelines(lines)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except IOError as e:
        print(f"Error reading/writing file '{file_path}': {e}")
       
def get_diff_stats(code1_filename, code2_filename):
    code1_filename = os.path.abspath(code1_filename)
    code2_filename = os.path.abspath(code2_filename)

    add_empty_line_to_file(code1_filename)
    add_empty_line_to_file(code2_filename)

    result = subprocess.run(
        ['git', 'diff', '--no-index', '--ignore-blank-lines', '-b', '--shortstat', code1_filename, code2_filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    output = result.stdout.strip()
    
    insertions = re.search(r'(\d+) insertions?\(\+\)', output)
    deletions = re.search(r'(\d+) deletions?\(-\)', output)

    added_lines = int(insertions.group(1)) if insertions else 0
    removed_lines = int(deletions.group(1)) if deletions else 0
    
    remove_last_empty_line(code1_filename)
    remove_last_empty_line(code2_filename)

    return added_lines, removed_lines

def get_file_line_count(file_path):

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            # non_empty_lines = [line for line in lines if line.strip()]
            return len(lines)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return 0
    except IOError as e:
        print(f"Error reading file '{file_path}': {e}")
        return 0
def get_diff_code(code1_filename, code2_filename):
    add_empty_line_to_file(code1_filename)
    add_empty_line_to_file(code2_filename)
    try:
        command = ["git", "diff", "-U9999", "-b", "--no-index", code1_filename, code2_filename]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        diff_code = "\n".join(str(result.stdout).split('\n')[5:])
        # with open(output_file, "w") as f:
        #     f.write(result.stdout)
        # print(f"Diff output saved to: {output_file}")
        remove_last_empty_line(code1_filename)
        remove_last_empty_line(code2_filename)
        return diff_code
    except Exception as e:
        print(f"An error occurred: {e}")

def Compute_retention_rate(data1,data2,output_file,compare_file, add_flag=False):
    result=[]
    
    i = 0
    count =0
    for entry in tqdm(data1):
       
        submission1_id=entry["submission1_id"]
        data3= next((item for item in data2 if item["submission1_id"] == submission1_id),None)
        
        code1_filename, code2_filename = save_temp_file(data1=entry, data2=data3,id=i+1,compare_file=compare_file)
        
        added_lines,removed_lines= get_diff_stats(code1_filename, code2_filename)
        data={}
        #data = data3.copy()
        data["now_id"]=i+1
        data["user_id"]=data3["user_id"]
        data["problem_id"]=data3["problem_id"]
        data["submission1_id"]=data3["submission1_id"]
        #data["code1"]=data3["code1"]
        data["code_content"]=data3["code_content"]
        data["origin_generated_text"]=data3["origin_generated_text"]
        data["code_test_status"]=data3["code_test_status"]
        data["code_test_score"]=data3["code_test_score"]
        data["TotalScore"]=data3["TotalScore"]
        if "flag" in data3:
            data["flag"]=data3["flag"]
        data["removed_lines"]=removed_lines
        data["added_lines"]=added_lines
        code1_lines = get_file_line_count(code1_filename)
        data["code1_lines"]=code1_lines
        retention_rate=1.0*(code1_lines-removed_lines)/code1_lines
        data["retention_rate"]=retention_rate


        if add_flag:
            if code1_lines>=25 and retention_rate<=0.15:
                data["flag"]=False
                count+=1
            

        result.append(data)
        i += 1
    if add_flag:
        print(f"flag is False, the count is {count}")
    save_data_to_json(result, output_file)
    
    return 0

def calculate_consistency(data, to_dir):
    temp_dir = os.path.join(to_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    submission_id = data["submission1_id"]
    code1_filename, code2_filename = save_python_file(
        data["code1"],
        data["code_content"],
        temp_dir,
        name1=f"{submission_id}_code1.py",
        name2=f"{submission_id}_code2.py",
    )

    py_file1, py_file2 = save_temp_file(
        code1_filename,
        code2_filename,
        temp_dir,
        name1=f"{submission_id}_code1.py",
        name2=f"{submission_id}_code2.py",
    )
    diff_code = get_diff_code(py_file1, py_file2)
    added_lines, removed_lines = get_diff_stats(py_file1, py_file2)
    a = added_lines
    b = removed_lines
    s = data["code1_lines"]
    consistency = (s - b) * 1.0 / (s + a - b) if (s + a - b) != 0 else 0.0

    data["diff_code"] = diff_code
    data["repaired_consistency"] = consistency

    for fpath in (code1_filename, code2_filename):
            try:
                os.remove(fpath)
            except Exception:
                pass
    return data

if __name__ == '__main__':
    
    parser=argparse.ArgumentParser(description="Compute the retention rate of code1 to another code.")
    parser.add_argument('--code1',type=str,required=False,default="./repairDataset/CRFLPDataset/test.json",help="the filename of source code(list)")
    parser.add_argument('--code2',type=str,required=False,default="./predict_evalResult_dir/baseline/baseline/Exec_baseline_result.json",help="the filename of new code(list)")
    parser.add_argument('--output_file',type=str,required=False,default="./predict_evalResult_dir/baseline/baseline/Exec_code1_baseline_result.json",help="the filename of result code1->code2")
    parser.add_argument('--compare_file',type=str,required=False,default="./compare_code1",help="the file of comparing code1 and code2")
    parser.add_argument('--add_flag',type=bool,required=False,default=False,help="the file of comparing code1 and code2")
    
    
    args=parser.parse_args()
    json_name1 = args.code1
    data1 = read_json(json_name1)
    
    json_name2 = args.code2
    data2 = read_json(json_name2)
    print(args.add_flag)
    Compute_retention_rate(data1,data2,args.output_file,args.compare_file, args.add_flag)
    # print("over")
    
    

