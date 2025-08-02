import json
import re
from datetime import datetime

class CustomEncoder(json.JSONEncoder):
    def encode(self, obj):
        result = super().encode(obj)
        result = result.replace('[\n            ', '[').replace('\n        ]', ']').replace('\n            ', ' ')
        return result

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

class CustomJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        return self.encode_dict(obj)

    def encode_dict(self, obj):
        items = []
        for key, value in obj.items():
            item = f'        "{key}": {json.dumps(value, ensure_ascii=False)}'
            items.append(item)
        return '    {\n' + ',\n'.join(items) + '\n    }'


def tojson(data: list, dir: str, mode='w', encoding='utf-8', need_print=True):
    try:
        with open(dir, mode, encoding=encoding) as file:
            file.write('[\n')
            for i, element in enumerate(data):
                file.write(CustomJSONEncoder().encode(element))
                if i < len(data) - 1:
                    file.write(',\n')
            file.write('\n]')
        if need_print:
            print(f"write into {dir} successfully")
    except Exception as e:
        print(f"fail to write into {dir}")
        print(e)

import os
import json
import hashlib
import pandas as pd
import numpy as np


class FileAlreadyExistsError(Exception):
    """Custom Exception: File already exists"""
    pass

def ensure_directory(file_path):
    """
    Check if the directory of the file path exists, create it if not.

    :param file_path: Full file path
    """
    # Get directory part
    directory = os.path.dirname(file_path)
    # Create directory if it does not exist
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_list_to_parquet(data_list, file_path):
    """
    Save a list object to a Parquet file, each element as a row.

    :param data_list: List object to save
    :param file_path: Parquet file path
    """
    df = pd.DataFrame(data_list)
    df.to_parquet(file_path, engine='pyarrow')

def read_parquet_to_df(file_path):
    """
    Read data from a Parquet file into a DataFrame.

    :param file_path: Parquet file path
    :return: DataFrame read from file
    """
    df = pd.read_parquet(file_path, engine='pyarrow')
    return df

def read_parquet_to_list(file_path):
    """
    Read data from a Parquet file into a list.

    :param file_path: Parquet file path
    :return: List read from file
    """
    df = pd.read_parquet(file_path, engine='pyarrow')
    return df.to_dict(orient='records')

def get_all_file_names(directory_path):
    """
    Get all file names in the specified directory.

    :param directory_path: Directory path
    :return: List of file names
    """
    try:
        entries = os.listdir(directory_path)
        file_names = [entry for entry in entries if os.path.isfile(os.path.join(directory_path, entry))]
        return file_names
    except FileNotFoundError:
        print(f"Error: The directory '{directory_path}' does not exist.")
        return []
    except PermissionError:
        print(f"Error: Permission denied for accessing the directory '{directory_path}'.")
        return []

def remove_comments(code):
    """
    Remove comments from code, including single-line and multi-line comments.

    :param code: Code string containing comments
    :return: Code string with comments removed
    """
    single_line_comment_pattern = r'//.*?$|#.*?$'
    multi_line_comment_pattern = r'/\*.*?\*/|\'\'\'.*?\'\'\'|""".*?"""'
    pattern = re.compile(
        single_line_comment_pattern + '|' + multi_line_comment_pattern,
        re.DOTALL | re.MULTILINE
    )
    cleaned_code = re.sub(pattern, '', code)
    return cleaned_code

def calculate_md5(input_string):
    """
    Calculate and return the MD5 hash value of a string.

    Args:
        input_string (str): The string to calculate the MD5 hash for.

    Returns:
        str: The MD5 hash value of the input string.
    """
    md5_hash = hashlib.md5()
    md5_hash.update(input_string.encode('utf-8'))
    return md5_hash.hexdigest()

def check_catalogue_exists(filepath):
    """
    Check if the specified path exists.

    Args:
        filepath (str): The path to check.

    Returns:
        bool: True if the path exists, False otherwise.
    """
    return os.path.exists(filepath)

def check_file_exists(filepath):
    """
    Check if the specified file exists.

    Args:
        filepath (str): The file path to check.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    return os.path.isfile(filepath)

def read_python_file(file_path):
    """Read the Python file at the specified path and return its content."""
    with open(file_path, 'r') as file:
        content = file.read()
    return content

def write_file_content_to_json(content, json_path):
    """Write content to a JSON file at the specified path."""
    data = {'file_content': content}
    with open(json_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def load_list_from_json(input_file_path):
    """Read a list from a JSON file."""
    with open(input_file_path, 'r') as json_file:
        data_list = json.load(json_file)
    return data_list

def save_list_to_json(lst, filepath):
    """
    Save a list to a JSON file at the specified path.

    Args:
        lst (list): The list to save.
        filepath (str): Path to save the JSON file.
    """
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime('%m%d%H%M')
        root, ext = os.path.splitext(filepath)
        backup_path = f"{root}_{timestamp}{ext}"
        try:
            with open(backup_path, 'w', encoding='utf-8') as json_file:
                json.dump(lst, json_file, ensure_ascii=False, indent=4)
            print(f"File '{filepath}' already exists. List backed up to '{backup_path}'.")
        except Exception as e:
            print(f"Error backing up list: {e}")
    ensure_dir(filepath)
    try:
        with open(filepath, 'w', encoding='utf-8') as json_file:
            json.dump(lst, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving list: {e}")

def load_list_from_jsonl(input_file_path):
    """
    Read a jsonl file and return a list, each element is a JSON object.

    :param file_path: Path to the jsonl file
    :return: List containing all JSON objects
    """
    data_list = []
    with open(input_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():
                json_obj = json.loads(line)
                data_list.append(json_obj)
    return data_list

def save_list_to_jsonl(data_list, file_path):
    """
    Save a list as a .jsonl file.

    Args:
        data_list: The list to save, each element should be a dict serializable to JSON.
        file_path: Path to save the file, should end with .jsonl.
    """
    ensure_dir(file_path)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data_list:
            json_line = json.dumps(item, ensure_ascii=False)
            f.write(json_line + '\n')
    print(f"Successfully saved {len(data_list)} records to file: {file_path}")

class CustomJSONEncoder1(json.JSONEncoder):
    def default(self, obj):
        # Handle numpy data types
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return super(CustomJSONEncoder1, self).default(obj)

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directory {directory} was created.")
    else:
        print(f"Directory {directory} already exists.")

def save_data_to_json(data, filepath):
    """
    Save data to a JSON file at the specified path, ensuring specific list fields are not wrapped, others are wrapped.

    Args:
        data (list): The list data to save.
        filepath (str): Path to save the JSON file.
    """
    try:
        if os.path.exists(filepath):
            raise FileAlreadyExistsError(f"File '{filepath}' already exists.")
        ensure_dir(filepath)
        with open(filepath, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, cls=CustomJSONEncoder1, ensure_ascii=False, indent=4)
        print(f"Data successfully saved to {filepath}")
    except Exception as e:
        print(f"Error saving data: {e}")


if __name__ == '__main__':
    print("here")


