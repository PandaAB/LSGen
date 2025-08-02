import re

CONTROL_FLOW_KEYWORDS = ("if", "elif", "else", "for", "while", "try", "except", "finally", "with", "def", "class")
CONTINUATION_KEYWORDS = {
    'if': ('elif', 'else'),
    'try': ('except', 'finally')
}

class Chunker:
    def __init__(self, source: str, msg: str):
        """
        Initialize Chunker, parse source code and error messages.
        """
        self.lines = [line.rstrip() for line in source.splitlines()]
        self.msg = msg
        self.start_index = None
        self.end_index = None
        self.cf_keyword = None

        self._locate_error()
        self._compute_bounds()

    def _locate_error(self):
        m = re.search(r"line (\d+)", self.msg)
        if not m:
            raise ValueError("The line number cannot be extracted from the message!")
        self.error_line = int(m.group(1))
        self.line_index = self.error_line - 1
        self.err_indent = len(self.lines[self.line_index]) - len(self.lines[self.line_index].lstrip(' '))

    def _compute_bounds(self):
        # If the error line is top-level (0 indentation), treat it as a single-line block
        if self.err_indent == 0:
            self.start_index = self.line_index
            self.end_index = self.line_index
            return
        # Search upwards for the starting point: find the first line with indentation < err_indent and treat it as the block start
        self.start_index, self.start_indent = self._pointer_up()
        # Check if the starting point is a control flow statement
        first = self.lines[self.start_index].lstrip()
        for kw in CONTROL_FLOW_KEYWORDS:
            if first.startswith(kw + ' ') or first.startswith(kw + ':'):
                self.cf_keyword = kw
                break
        # Search downwards for the endpoint
        self.end_index = self._pointer_down()

    def _pointer_up(self):
        for i in range(self.line_index, -1, -1):
            if not self.lines[i].strip():
                continue
            indent_i = len(self.lines[i]) - len(self.lines[i].lstrip(' '))
            if indent_i < self.err_indent:
                return i, indent_i
        return 0, len(self.lines[0]) - len(self.lines[0].lstrip(' '))

    def _pointer_down(self):
        """
        Search downwards from start_index for the first line with indentation <= start_indent, treating it as the line before the block ends.
        For control flow blocks, allow continuation keywords to extend the block.
        """
        n = len(self.lines)
        for j in range(self.start_index + 1, n):
            if not self.lines[j].strip():
                continue
            indent_j = len(self.lines[j]) - len(self.lines[j].lstrip(' '))
            if indent_j <= self.start_indent:
                if self.cf_keyword and self.cf_keyword in CONTINUATION_KEYWORDS:
                    token = self.lines[j].lstrip().split()[0].rstrip(':')
                    if token in CONTINUATION_KEYWORDS[self.cf_keyword]:
                        continue
                return j - 1
        return n - 1

    def get_chunk(self) -> str:
        """Return the extracted code block string."""
        return '\n'.join(self.lines[self.start_index:self.end_index+1])

    def reintegrate(self, repaired_chunk: str) -> str:
        """
        Reinsert the repaired block into the original code and return the complete source code.
        Each line of the repaired block will be re-indented based on the indentation of the original block's starting point.
        """
        original_line = self.lines[self.start_index]
        indent_str = original_line[:len(original_line) - len(original_line.lstrip())]
        repaired_lines = [indent_str + line for line in repaired_chunk.splitlines()]
        new_lines = self.lines[:self.start_index] + repaired_lines + self.lines[self.end_index+1:]
        return "\n".join(new_lines)

if __name__ == "__main__":
    with open("demo.txt", "r") as f:
        source = f.read()
    msg = "SyntaxError at line 14: unsupported operand type(s)"
    chunker = Chunker(source, msg)
    # print("Chunk:")
    print(chunker.get_chunk())
    # with open("demo2.txt", "r") as f:
    #     a = f.read()
    # print(chunker.reintegrate(a))
