from utils.jsonTools import load_json, tojson
import argparse

def get_final_data(data1, data2, output_path):
    id = set()
    d = []
    for each in data1:
        id.add(each["submission1_id"])
        d.append(each)
    for each in data2:
        if each["submission1_id"] not in id:
            d.append(each)
    tojson(d, output_path)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--Init_file", type=str, required=True)
    parser.add_argument("--Refine_file", type=str, required=True)
    parser.add_argument("--output_file", type=str, required=True)
    args = parser.parse_args()

    data1 = load_json(args.Refine_file)
    data2 = load_json(args.Init_file)
    get_final_data(data1=data1, data2=data2, output_path=args.output_file)
