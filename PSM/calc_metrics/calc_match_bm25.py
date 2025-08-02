from rank_bm25 import BM25Okapi
from PSM.parser.anonymize import anonymize_code

def tokenize_code(code):
    lines = code.split("\n")
    tokens = []
    for line in lines:
        tokens.extend(line.split(" "))
    return [token for token in tokens if token.strip()]


def calculate_bm25_normalization_score(score_list):
    sorted_score_list = sorted(score_list)
    min = sorted_score_list[0]
    max = sorted_score_list[len(sorted_score_list)-1]
    res = []
    for bm25_score in score_list:
        if max - min == 0:
            res.append(0)
        else:
            res.append((bm25_score - min) / (max - min))
    return res


def corpus_bm25_match(corpus, query):
    corpus = [anonymize_code(doc) for doc in corpus]
    tokenized_corpus = [tokenize_code(doc) for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    
    query = anonymize_code(query)
    tokenized_query = tokenize_code(query)
    doc_scores = bm25.get_scores(tokenized_query)

    res = calculate_bm25_normalization_score(doc_scores)

    return res


