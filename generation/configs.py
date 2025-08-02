import argparse
import yaml
from dataclasses import dataclass, fields
from typing import Any
    
@dataclass
class InferenceConfig:
    model_path: str
    eval_dataset_name: str
    dp_size: int
    tp_size: int
    dtype: str
    dp_master_ip: str
    dp_master_port: int
    data_path_dir: str
    debug_mode: bool
    language: str
    max_input_tokens: int
    max_output_tokens: int
    save_file_path: str
    system_prompt: str
    temperature: int
    top_p: int
    gpu_memory_utilization: float
    use_lora: bool = False
    lora_path: str = ""
    without_context: bool = False
    eval_mode: str = "test"
    prompt_mode: str = "split"
    refTopk: int = 5
    retrieval_data_file: str = "dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_test_processed_pair.json"
    batch_size: int = 1

def load_config(config_path: str) -> InferenceConfig:
    with open(config_path, 'r') as file:
        config_data = yaml.safe_load(file)
    return InferenceConfig(**config_data)