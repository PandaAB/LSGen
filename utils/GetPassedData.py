from utils.jsonTools import load_json, tojson
import argparse

def get_data(data, output_path, mode="pass"):
    d = []
    for each in data:
        if mode == "pass":
            if each["code_test_score"] == each["TotalScore"] and each["TotalScore"] != 0:
                d.append(each)
        elif mode == "buggy":
            if each["code_test_score"] == each["TotalScore"] and each["TotalScore"] != 0:
                pass
            else:
                d.append(each)
    tojson(d, output_path)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str, required=True)
    parser.add_argument("--mode", type=str, choices=["pass", "buggy"], required=True)
    parser.add_argument("--output_file", type=str, required=True, help="Path to output file")
    args = parser.parse_args()

    data = load_json(args.input_file)
    get_data(data, output_path=args.output_file, mode=args.mode)
