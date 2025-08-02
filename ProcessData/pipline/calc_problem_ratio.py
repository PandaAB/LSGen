import pandas as pd
import argparse
import os
import matplotlib.pyplot as plt
import numpy as np

def load_csv(problem_id, folder="dataset/Project_CodeNet/metadata"):
    """
    Load the CSV file based on problem_id.
    """
    file_path = os.path.join(folder, f"{problem_id}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist.")
    df = pd.read_csv(file_path)
    return df

def filter_by_language(df, language):
    """
    Filters the data in the anguage column equal to the given language.
    """
    return df[df['language'] == language]

def deduplicate_by_user(df):
    """
    After user_id is de-duplicated and sorted in ascending order by date, only the data submitted for the first time is retained for each user_id.
    """
    df_sorted = df.sort_values(by='date')
    df_dedup = df_sorted.drop_duplicates(subset='user_id', keep='first')
    return df_dedup

def calculate_ratio(df):
    """
    Calculate the ratio of the number whose status is "Accepted" to the total.
    """
    total = len(df)
    if total == 0:
        return 0.0
    accepted = len(df[df['status'] == 'Accepted'])
    return accepted / total

def get_ratio(problem_id, language):
    df = load_csv(problem_id)
    df_filtered = filter_by_language(df, language)
    df_dedup = deduplicate_by_user(df_filtered)
    ratio = calculate_ratio(df_dedup)
    # print(f">>> {problem_id} Accepted ratio: {ratio:.4f}")
    return ratio

def plot_pass_rate_distribution(PID_ratio, save_path, bin_size=0.1):
    """
    According to PID_ratio (title pass rate dictionary), the pass rate distribution is counted according to the specified interval size (default 0.1), and a bar chart is drawn.

    Parameters:
    PID_ratio: dict, where the key is the topic ID and the value is the pass rate (floating point number between 0 and 1).
    bin_size: float, the range size. For example,0.1 indicates that the pass rate is divided into 10 ranges: [0,0.1), [0.1,0.2),..., [0.9,1.0]
    """

    pass_rates = list(PID_ratio.values())
    
    bins = np.arange(0, 1 + bin_size, bin_size)
    
    counts, _ = np.histogram(pass_rates, bins=bins)
    
    bin_centers = bins[:-1] + bin_size / 2
    
    plt.figure(figsize=(8, 5))
    plt.bar(bin_centers, counts, width=bin_size * 0.9, align='center', edgecolor='black')
    plt.xlabel('Pass rate range')
    plt.ylabel('Problem distribution numbers')
    plt.title('Problem pass rate distribution')
    plt.xticks(bins)
    plt.yticks(np.arange(0, max(counts) + 1, 3))
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig(save_path)
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Calculates the proportion of first submissions where status is 'Accepted' for given problem_id and language."
    )
    parser.add_argument("--problem_id", type=str, help="problem_id")
    parser.add_argument("--language", type=str, default="Python", help="language")
    args = parser.parse_args()
    get_ratio(args.problem_id, args.language)
    # get_ratio("p02919", "Python")
