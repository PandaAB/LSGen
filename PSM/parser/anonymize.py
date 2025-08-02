import ast
import astor

class VariableAnonymizer(ast.NodeTransformer):
    def __init__(self):
        super().__init__()
        self.variable_map = {}
        self.counter = 1

    def _get_anonymous_name(self, var_name):
        if var_name not in self.variable_map:
            self.variable_map[var_name] = f"v{self.counter}"
            self.counter += 1
        return self.variable_map[var_name]

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store) or isinstance(node.ctx, ast.Load):
            node.id = self._get_anonymous_name(node.id)
        return node

    def visit_arguments(self, node):
        for arg in node.args:
            arg.arg = self._get_anonymous_name(arg.arg)
        return node

def anonymize_code(code):
    tree = ast.parse(code)
    anonymizer = VariableAnonymizer()
    anonymized_tree = anonymizer.visit(tree)
    anonymized_code = astor.to_source(anonymized_tree)
    return anonymized_code

if __name__ == "__main__":
    code = "\n\ndef main():\n    for i in range(int(input())):\n        a=int(input())+int(input())\n        if a>=10**80:\n            print(\"overflow\")\n        else:\n            print(a)\n            \n    \nif __name__ == '__main__':\n    main()\n"
    anonymized_code = anonymize_code(code)
    print(anonymized_code)