#from ExecutiveProgram.ExecRestRequest import APIManager
from codeTool.ExecutiveProgram.FileIO import FileHandlerSingleton 
from codeTool.ExecutiveProgram.Worker import Checker, Worker, Program_Submission, Quesion_Test_Point_objectList
from codeTool.utils.utils import load_list_from_json, save_list_to_json, save_data_to_json, check_catalogue_exists, check_file_exists
from tqdm import tqdm
import multiprocessing
import argparse
import os

class EvalProcess:
    def __init__(self, 
        EvalOject_Path,\
        test_directory_prefix_url,\
        Write_prefix_url,\
        CODE_KEY,\
        language = "Python",\
        AddCompile = False):
        self.CODE_KEY = CODE_KEY
        self.EvalOject_path = EvalOject_Path
        self.EvalOject_List = load_list_from_json(self.EvalOject_path)

        file_name_with_ext = os.path.basename(EvalOject_Path)
        file_name = os.path.splitext(file_name_with_ext)[0]
        self.resotreFile_Path = Write_prefix_url + f"Exec_{file_name}.json"
        self.test_directory_prefix_url = test_directory_prefix_url
        self.language = language
        self.worker = Worker()
        self.checker = Checker()
        FileHandlerSingleton.initialize()
        self.AddCompile = AddCompile

    def AddPsubmitCompile2item(self, Psubmit, item):
        if Psubmit.CompileResult["files"]["stderr"] != "":
            item["code1_compile_status"] = Psubmit.CompileResult["files"]["stderr"]
        else:
            item["code1_compile_status"] = "Compile Success"

    def AddPsubmitResult2item(self, Psubmit, item):

        TotalScore = len(Psubmit.CheckRunResultList)
        result_mapping = {
            'Accepted': 1,
            'Time Limit Exceeded': -1,
            'Nonzero Exit Status': -2,
            'Memory Limit Exceeded': -3,
            'Output Limit Exceeded': -4,
            'Wrong Answer': 0
        }

        CheckRunResultList = [result_mapping[result] for result in Psubmit.CheckRunResultList]

        Score = CheckRunResultList.count(1)
        item["code_test_status"] = CheckRunResultList
        item["code_test_score"] = Score
        item["TotalScore"] = TotalScore
 
        
    def getProblem_id(self, str):
        if str[0] != 'p':
            return f"p{str}"
        else:
            return str
        
    def Process_For_Single_EvalObject(self, item):
        problem_id = self.getProblem_id(item['problem_id'])
        
        test_directory_path = self.test_directory_prefix_url + f"{problem_id}/"
        if check_catalogue_exists(test_directory_path) == False:
            print(f"FilePath {test_directory_path} is not exist")
            return 
        Test_List = Quesion_Test_Point_objectList()
        Test_List.inint_Tlist_by_FileHandlerSingleton(FileDirectory=test_directory_path)
        submission1_id = item["submission1_id"]
        Compile_File_name = f"{submission1_id}.py"
        # CodeContent =  item["code_content"]
        CodeContent =  item[self.CODE_KEY]
        Psubmit = Program_Submission(Compile_File_name, CodeContent, self.language)
        self.worker.Run_Program_By_One_All_Point(Psubmit, Test_List, deBug = False)
        self.checker.Check_Run_Result(Psubmit, Test_List)
        self.AddPsubmitResult2item(Psubmit,item)
        return item
    
    def Process_For_Single_CompileObject(self, item):
        problem_id = self.getProblem_id(item['problem_id'])
        
        test_directory_path = self.test_directory_prefix_url + f"{problem_id}/"
        if check_catalogue_exists(test_directory_path) == False:
            print(f"FilePath {test_directory_path} is not exist")
            return 
        Test_List = Quesion_Test_Point_objectList()
        Test_List.inint_Tlist_by_FileHandlerSingleton(FileDirectory=test_directory_path)
        submission1_id = item["submission1_id"]
        Compile_File_name = f"{submission1_id}.py"
        CodeContent =  item[self.CODE_KEY]
        Psubmit = Program_Submission(Compile_File_name, CodeContent, self.language)
        self.worker.Run_Program_By_One_All_Point(Psubmit, Test_List, deBug = False)
        # print(Psubmit)
        self.AddPsubmitCompile2item(Psubmit, item)
        return item
    
        
    def ProcessAllData(self):
        if self.AddCompile == True:
            print(">>> Add Compile Result to Item")
            with multiprocessing.Pool(processes=8) as pool: 
                ResultDataList =  list(tqdm(pool.imap(self.Process_For_Single_CompileObject, self.EvalOject_List), total=len(self.EvalOject_List), desc="Processing elements", colour="magenta"))
        else:
            print(">>> Add Test Result to Item")
            with multiprocessing.Pool(processes=8) as pool: 
                ResultDataList =  list(tqdm(pool.imap(self.Process_For_Single_EvalObject, self.EvalOject_List), total=len(self.EvalOject_List), desc="Processing elements", colour="magenta"))
        
        print(f" >>> The number of final result pairs are {len(ResultDataList)}.")

        save_data_to_json(ResultDataList, self.resotreFile_Path)
        

    def ProcessAllData_Sequential_Execution(self):
        ResultDataList = []
        for EvalOject in tqdm(self.EvalOject_List, desc="Processing elements"):
            item = self.Process_For_Single_EvalObject(EvalOject)
            ResultDataList.append(item)
    
        save_data_to_json(ResultDataList, self.resotreFile_Path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluation Code Generation Script")
    parser.add_argument('--EvalOject_Path', type=str, default="", required=True, help='Input data for evaluation')
    parser.add_argument('--test_directory_prefix_url', type=str, default="./merged_test_cases/", help='test cases directory')
    parser.add_argument('--Write_prefix_url', type=str, default= "./predict_dir/baseline", help='Output file path')
    parser.add_argument('--CODE_KEY', type=str, default="code2", help='Code fields that need to be evaluated')
    parser.add_argument('--AddCompile', default=False, action='store_true', help='Add compile result to item')
    args = parser.parse_args()

    EXECUTION_ALL = True

    if EXECUTION_ALL == True:
        process = EvalProcess(EvalOject_Path = args.EvalOject_Path, \
                              test_directory_prefix_url = args.test_directory_prefix_url,\
                              Write_prefix_url = args.Write_prefix_url,\
                              CODE_KEY = args.CODE_KEY, AddCompile=args.AddCompile)
        print(f"**The code currently under review is {args.CODE_KEY}**")
        process.ProcessAllData()