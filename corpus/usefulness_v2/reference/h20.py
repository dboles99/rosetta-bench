class TextBuffer:
    def __init__(self, text=""):
        self._text = text
        self._undo = []  # each step is a list of (kind, pos, string) operations
        self._redo = []
        self._merge_end = None  # end of the last insert while merging is possible

    @property
    def text(self):
        return self._text

    def _apply(self, op, inverse=False):
        kind, pos, s = op
        if (kind == "insert") != inverse:
            self._text = self._text[:pos] + s + self._text[pos:]
        else:
            self._text = self._text[:pos] + self._text[pos + len(s):]

    def insert(self, pos, s):
        if not 0 <= pos <= len(self._text):
            raise IndexError("insert position out of range")
        if s == "":
            return
        op = ("insert", pos, s)
        self._apply(op)
        if self._merge_end is not None and pos == self._merge_end:
            self._undo[-1].append(op)
        else:
            self._undo.append([op])
        self._merge_end = pos + len(s)
        self._redo.clear()

    def delete(self, pos, length):
        if pos < 0 or length < 0 or pos + length > len(self._text):
            raise IndexError("delete range out of range")
        if length == 0:
            return
        op = ("delete", pos, self._text[pos:pos + length])
        self._apply(op)
        self._undo.append([op])
        self._merge_end = None
        self._redo.clear()

    def undo(self):
        self._merge_end = None
        if not self._undo:
            return False
        step = self._undo.pop()
        for op in reversed(step):
            self._apply(op, inverse=True)
        self._redo.append(step)
        return True

    def redo(self):
        self._merge_end = None
        if not self._redo:
            return False
        step = self._redo.pop()
        for op in step:
            self._apply(op)
        self._undo.append(step)
        return True

    def history_size(self):
        return len(self._undo)
