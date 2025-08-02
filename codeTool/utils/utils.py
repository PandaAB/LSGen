import os
import json
import hashlib


def calculate_md5(input_string):
    """
    Compute and return the MD5 hash value of the input string.

    Args:
        input_string (str): The string for which to compute the MD5 hash.

    Returns:
        str: The MD5 hash value of the input string.
    """
    md5_hash = hashlib.md5()
    
    md5_hash.update(input_string.encode('utf-8'))
    
    return md5_hash.hexdigest()

def check_catalogue_exists(filepath):
    """
    Check if a file exists at the specified path.

    Args:
        filepath (str): The path of the file to check.

    Returns:
        bool: Returns True if the file exists; otherwise, returns False.
    """
    return  os.path.exists(filepath)


def check_file_exists(filepath):
    """
    Check if a file exists at the specified path.

    Args:
        filepath (str): The path of the file to check.

    Returns:
        bool: Returns True if the file exists; otherwise, returns False.
    """
    return  os.path.isfile(filepath)

def read_python_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content

def write_file_content_to_json(content, json_path):
    data = {'file_content': content}
    with open(json_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def load_list_from_json(input_file_path):
        with open(input_file_path, 'r') as json_file:
            data_list = json.load(json_file)
        return data_list
    
def save_list_to_json(lst, filepath):
    """
    Save a list to a JSON file at the specified path.

    Args:
        lst (list): The list to be saved.
        filepath (str): The path where the JSON file will be saved.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as json_file:
            json.dump(lst, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving the list: {e}")


class CustomJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        return self.encode_dict(obj)
        

    def encode_dict(self, obj):   
        items = []
        for key, value in obj.items():
            item = f'        "{key}": {json.dumps(value, ensure_ascii=False)}'
            items.append(item)
        return '    {\n' + ',\n'.join(items) + '\n    }'

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directory {directory} was created.")
    else:
        print(f"Directory {directory} already exists.")

def save_data_to_json(data, filepath):
    """
    Store data in a JSON file at the specified path, ensuring that specific list fields do not have newlines, while other fields do.
    Args:
    data (list): The list of data to be stored.
    filepath (str): The path where the JSON file will be saved.
    """
    try:
        ensure_dir(filepath)
        with open(filepath, 'w', encoding='utf-8') as json_file:
            json_file.write('[\n')
            for i, element in enumerate(data):
                json_file.write(CustomJSONEncoder().encode(element))
                if i < len(data) - 1:
                    json_file.write(',\n')
            json_file.write('\n]')
        print(f"Data has been successfully saved to {filepath}")
    except Exception as e:
        print(f"Error saving data: {e}")

def File2String(file_path, json_output_path):
    
    os.makedirs(os.path.dirname(json_output_path), exist_ok=True)

    content = read_python_file(python_file_path)
    print(content)
    write_file_content_to_json(content, json_output_path)
    print("writing")
if __name__ == '__main__':
    print("here")
    python_file_path = '/home/develop/xxx/CodeFixProject/CodeTool/ConstructDataPair/test2.py'
    json_output_path = '/home/develop/xxx/CodeFixProject/CodeTool/utlis/out_file/CodeString.json'
    
    File2String(python_file_path ,json_output_path)
    
   

    