from codeTool.ExecutiveProgram.ExecRestRequest import APIManager
import json
import re
from codeTool.ExecutiveProgram.FileIO import FileHandlerSingleton

class Program_Submission:
    def __init__(self, Compile_File_name, CodeContent, Language = "Python", CopyIn_fileId = None):
        self.Compile_File_name = Compile_File_name
        
        self.CodeContent = CodeContent
        self.CopyIn_fileId = CopyIn_fileId
        self.Language = Language
        if self.Language == "Python":
            Execute_File_name_without_type = self.Compile_File_name.split(".")[0]
            self.SubmissionId = Execute_File_name_without_type
            self.Execute_File_name = f"__pycache__/{Execute_File_name_without_type}.cpython-311.pyc"
        else:
            raise ValueError(">>> language value is wrong")
        self.Is_Compile = False 
        self.Compile_Status = None
        self.CompileResult = None 
        self.stderr = None 
        
        self.ResultStatus = None 
        self.RunResultList = [] 
        self.CheckRunResultList = [] 
        
    def __str__(self):
        return (f"Compile_File_name: {self.Compile_File_name}\n"
                f"SubmissionId: {self.SubmissionId}\n"
                f"CodeContent: {self.CodeContent}\n"
                f"CopyIn_fileId: {self.CopyIn_fileId}\n"
                f"Language: {self.Language}\n"
                f"Execute_File_name: {self.Execute_File_name}\n"
                f"Compile_Status: {self.Compile_Status}\n"
                f"CompileResult: {self.CompileResult}\n"
                f"stderr: {self.stderr}\n"
                f"Is_Compile: {self.Is_Compile}\n"
                f"ResultStatus: {self.ResultStatus}\n"
                f"RunResultList: {self.RunResultList}\n"
                f"CheckRunResultList: {self.CheckRunResultList}")
        
    #def Print_CheckRunResultList
    
class Quesion_Test_Point_object:
    def __init__(self, Test_Point_Input, Test_Point_Output):
        self.Test_Point_Input = Test_Point_Input
        self.Test_Point_Output = Test_Point_Output
  
    def __str__(self):
        return (f"Test_Point_Input: {self.Test_Point_Input}\n"
                f"Test_Point_Output: {self.Test_Point_Output}\n")
    
class Quesion_Test_Point_objectList:
    def __init__(self):
        self.Tlist = []
    def Insert_Test_Point(self, Test_Point_object):
        self.Tlist.append(Test_Point_object)
    def Get_Item(self, i):
        return  self.Tlist[i]

    def inint_Tlist_by_FileHandlerSingleton(self, FileDirectory, deBug = False):
        instance_info = FileHandlerSingleton(FileDirectory)
        if deBug == True:
            print("Input Files:")
            print(instance_info['input_files'])
            print("Output Files:")
            print(instance_info['output_files'])
            
        # num_elements = len(instance_info['input_files'])
        # for i in range (num_elements):
        #     item = Quesion_Test_Point_object(instance_info['input_files'][i], instance_info['output_files'][i])
        #     self.Insert_Test_Point(item)
        
        for key, value in instance_info['input_files'].items():
            data = Quesion_Test_Point_object(value, instance_info['output_files'][key])
            self.Insert_Test_Point(data)

            
        if deBug == True:
            print(str(self.Tlist[0]))
            print(str(self.Tlist[1]))
            print(str(self.Tlist[2]))
class Worker: 
    def __init__(self):
        self.url_prefix = 'http://127.0.0.0:5050/'
        self.apimanager = APIManager(self.url_prefix)
    
    def Extract_Compile_Information(self, Compile_Result_Data, Psubmit):
        
        Psubmit.CompileResult = Compile_Result_Data
        Psubmit.Compile_Status = Compile_Result_Data["status"]
        if Psubmit.Compile_Status != "Accepted":
            Psubmit.stderr = Compile_Result_Data["files"]["stderr"]
            return 
        Psubmit.CopyIn_fileId = Compile_Result_Data["fileIds"][Psubmit.Execute_File_name]
        Psubmit.Is_Compile = True
    
    def Extract_Execution_Information(self, Run_Result_Data, Psubmit):
        Psubmit.RunResultList.append(Run_Result_Data)
        
    def Run_Program_By_One_Test_Point(self, Psubmit, Test_Point_Input, deBug = False):
        if Psubmit.Is_Compile == False:
            Json_Text_response = self.apimanager.Compile_Program(Psubmit.Compile_File_name, Psubmit.CodeContent, Psubmit.Language)
            Compile_Result_Data = json.loads(Json_Text_response)
            if Compile_Result_Data[0]["status"] == "File Error":
                print(Psubmit)
                print(Compile_Result_Data[0])
                raise ValueError("Compile_Result_Data Status Value is \"File Error\", Check file or directory name")
            if deBug == True:
                print(type(Compile_Result_Data))
                print(Compile_Result_Data)
                #input()
            self.Extract_Compile_Information(Compile_Result_Data[0], Psubmit)
        
        if Psubmit.Is_Compile == True and Psubmit.Compile_Status == "Accepted":
            Json_Text_response = self.apimanager.Execute_Program_After_Compile(Psubmit.CopyIn_fileId, Psubmit.Execute_File_name, Test_Point_Input, Psubmit.Language)
            Run_Result_Data = json.loads(Json_Text_response)
            self.Extract_Execution_Information(Run_Result_Data[0], Psubmit)

    def Run_Program_By_One_All_Point(self, Psubmit, TestPointList, deBug = False):
        for item in TestPointList.Tlist:
            self.Run_Program_By_One_Test_Point(Psubmit,item.Test_Point_Input, deBug)
        self.apimanager.Delete_File_By_Fileid(Psubmit.CopyIn_fileId)

class Checker:

    def Check_consistency(self, str1, str2, deBug = False):
        """
        Perform a format check, remove extra whitespace and newline characters from two strings,and check if they are completely identical.

        Args:
            str1 (str): The first string
            str2 (str): The second string

        Returns:
            bool: Returns True if the processed strings are identical, otherwise returns False
        """
        def normalize(s):
            s = re.sub(r'[ \t]+(?=\n)|(?<=\S)[ \t]+$', '', s, flags=re.MULTILINE)
            s = s.strip()
            s = s.replace('\r\n', '\n').replace('\r', '\n')
            return s

        normalized_str1 = normalize(str1)
        normalized_str2 = normalize(str2)
        if deBug == True:
            print(f">>> {normalized_str1}")
            print(f">>> {normalized_str2}")
            
        return normalized_str1 == normalized_str2
    
    def Check_Run_Result(self, Psubmit:Program_Submission, Test_List):
        if Psubmit.Compile_Status == False:
            Psubmit.ResultStatus = "COMPILE_ERROR"
            
        else:
            i = 0
            for item in Psubmit.RunResultList:
                status = None
                if item["status"] != "Accepted": #TLE MLE OLE
                    status = item["status"]
                    Psubmit.ResultStatus = status
                else:
                    Run_str = item["files"]["stdout"]
                    
                    Real_str = Test_List.Get_Item(i).Test_Point_Output
                    # print(f"i = {i}")
                    # print(f"real_str = {Real_str}")
                    CheckStatus = self.Check_consistency(Run_str,Real_str)
                    if CheckStatus == False:
                        status = "Wrong Answer"
                    else:
                        status = "Accepted"
                    if Psubmit.ResultStatus == None or (Psubmit.ResultStatus == "Accepted" and status == "Wrong Answer"):
                        Psubmit.ResultStatus = status

                        
                Psubmit.CheckRunResultList.append(status)
                i += 1 
                
            if  Psubmit.ResultStatus == None:
                Psubmit.ResultStatus = "Accepted"
            

if __name__ == '__main__':
    EXECUTION_ONE = True
    EXECUTION_ALL = True
    CHECK_TEST1 = False
    
    FileDictory = "/home/develop/xxx/CodeFixProject/CodeDatasets/merged_test_cases/p00010"
    checker = Checker()
    w = Worker()
    Compile_File_name = "s001.py"
    CodeContent = "for i in range(int(input())):\n    x1, y1, x2, y2, x3, y3 = map(float, input().split())\n    c = (x1-x2)**2 + (y1-y2)**2\n    a = (x2-x3)**2 + (y2-y3)**2\n    b = (x3-x1)**2 + (y3-y1)**2\n    # 16s^2\n    s = 2*(a*b + b*c + c*a) - (a*a + b*b + c*c)\n\n    px = (a*(b+c-a)*x1 + b*(c+a-b)*x2 + c*(a+b-c)*x3) / s\n    py = (a*(b+c-a)*y1 + b*(c+a-b)*y2 + c*(a+b-c)*y3) / s\n\n    ar = a**0.5\n    br = b**0.5\n    cr = c**0.5\n\n    r = ar*br*cr / ((ar+br+cr)*(-ar+br+cr)*(ar-br+cr)*(ar+br-cr))**0.5\n\n    print(\"{:>.3f}\".format(px),\"{:>.3f}\".format(py),\"{:>.3f}\".format(r))"
    Psubmit = Program_Submission(Compile_File_name, CodeContent)
    
    
    
    if CHECK_TEST1 == True:
        str1 = "  Hello, world! \nThis is a test.   \n  "
        str2 = "Hello, world!\nThis is a test.\n"
        result = checker.Check_consistency(str1, str2)
        print(result)

    if EXECUTION_ONE == True:    
        Test_Point_Input = "1\n0.0 0.0 2.0 0.5127281311709682 2.0 2.0"
        w.Run_Program_By_One_Test_Point(Psubmit, Test_Point_Input)
        print(Psubmit)
        print(type(Psubmit))
        input()
    if EXECUTION_ALL == True:
        Test_List = Quesion_Test_Point_objectList()
        Test_List.inint_Tlist_by_FileHandlerSingleton(FileDirectory=FileDictory)
        # Q1 = Quesion_Test_Point_object("1\n0.0 0.0 2.0 0.5127281311709682 2.0 2.0", "0.744 1.256 1.460\n\n")
        # Q2 = Quesion_Test_Point_object("1\n0.0 0.0 2.4487612247110815 0.5127281311709682 2.0 2.0", "1.087 0.913 1.420\n\n")
        # Q3 = Quesion_Test_Point_object("1\n0.0 0.0 2.4487612247110815 0.5127281311709682 2.0 2.033916337250816", "1.082 0.936 1.431\n\n")
        # Test_List.Insert_Test_Point(Q1)
        # Test_List.Insert_Test_Point(Q2)
        # Test_List.Insert_Test_Point(Q3)
        w.Run_Program_By_One_All_Point(Psubmit, Test_List)
        checker.Check_Run_Result(Psubmit, Test_List)
        print(Psubmit)