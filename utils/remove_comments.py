import re

# def remove_comments(code):
    # """
    # Remove comments from code, including single-line comments and multi-line comments
    # :param code: Code string containing comments
    # :return: The code string after the comment is removed
    # """
    # # Defines regular expressions used to match single - and multi-line comments
    # # single_line_comment_pattern = r'//.*?$|#.*?$'
    # # multi_line_comment_pattern = r'/\*.*?\*/|\'\'\'.*?\'\'\'|""".*?"""'
    # single_line_comment_pattern = r'#.*?$'
    # multi_line_comment_pattern = r'\'\'\'.*?\'\'\'|""".*?"""'
    
    # # Combined regular expression
    # pattern = re.compile(
    #     single_line_comment_pattern + '|' + multi_line_comment_pattern,
    #     re.DOTALL | re.MULTILINE
    # )

    # # Use regular expressions to remove comments
    # cleaned_code = re.sub(pattern, '', code)
    
    # return cleaned_code

def remove_comments(code):
    """
    Remove comments from code, including single-line comments and multi-line comments
    :param code: Code string containing comments
    :return: The code string after the comment is removed
    """
    
    string_pattern = r'\".*?\"|\'.*?\''
    
    single_line_comment_pattern = r'(?<!\\)#.*?$'

    multi_line_comment_pattern = r'\'\'\'(.*?)\'\'\'|"""(.*?)"""'
    
    pattern = re.compile(
        string_pattern + '|' + single_line_comment_pattern + '|' + multi_line_comment_pattern,
        re.DOTALL | re.MULTILINE
    )

    def repl(match):
        if match.group(0).startswith(("'", '"')):
            return match.group(0)
        return ''

    return re.sub(pattern, repl, code)

if __name__ == '__main__':
    code_with_comments = "import sys\n\n#\u6700\u5927\u516c\u7d04\u6570\ndef gcd(x, y):\n    s = x // y\n    r = x % y\n    if r == 0:\n        return y\n    else:\n        return gcd(y, r)\n\n#\u6700\u5c0f\u516c\u500d\u6570\ndef lcm(x, y):\n    return x*y/gcd(x, y)\n\ndef main():\n    #print (\"a\")\n    for line in iter(sys.stdin.readline, \"\"):\n        print (line)\n        #tmp = sys.stdin.readline().split(\" \")\n        #print (\"b\")\n        tmp = line.split(\" \")\n    \n        a = int(tmp[0])\n        b = int(tmp[1])\n        #print (\"a=\"+str(a))\n        #print (\"b=\"+str(b))\n        #b = sys.stdin.readline()\n        #print (\"d\")\n        if a > b:\n            c = a\n            d = b\n        else:\n            c = b\n            d = a\n\n        print (str(gcd(c, d)) + \" \" + str(int(lcm(c,d))))\n\n        #tmp = sys.stdin.readline()\n        #if len(tmp) == 1:\n        #    break\n        #else:\n        #    tmp = tmp.split(\" \")\n\n    #print (\"exit\")\n     \nif __name__ == \"__main__\":\n    main()"

    code_with_comments = "a = b\n#nmoin\nc = d # nfdoinif\n"
    cleaned_code = remove_comments(code_with_comments)

    print("ok")
    print(cleaned_code)