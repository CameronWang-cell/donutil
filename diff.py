from typing import Literal
import re
from dataclasses import dataclass

"""
use case
diff = Diff.from_file("path/to/your/diff")
for hunk in diff.hunks:
    hunk.old_start
    hunk.content
    for line in hunk.old_lines:
        line.type
        line.index
        line.line_content
    for line in hunk.new_lines:
        line.type
        line.index
        line.line_content
"""


class Line:
    """
    a line of diff
    interface:
        type
        index
        line_content
    """
    def __init__(self, type: Literal["added", "removed", "context"], index: int, line_content: str):
        self.type: Literal["added", "removed", "context"] = type
        self.index: int = index
        self.line_content: str = line_content

    def __str__(self):
        match self.type:
            case "added":
                t = "[+]"
            case "removed":
                t = "[-]"
            case "context":
                t = "ctx"
        return f"{t}   {self.index: <6} {self.line_content}"



@dataclass
class Head:
    old_start: int
    old_len: int
    old_end: int
    new_start: int
    new_len: int
    new_end: int



class Hunk:
    """
    core class, a hunk in diff file, iterable(old/new lines)
    interface:
        old_start, old_len, old_end
        new_start, new_len, new_end
        content
        content_wo_head
        old_lines(iterable)
        new_lines(iterable)
    """
    def __init__(self, hunk_content: str):
        self.head: Head = self.__parse_head(hunk_content)
        self.content = hunk_content
        self.content_wo_head = self.__parse_content_wo_head(hunk_content)
        self.old_lines: list[Line] = self.__parse_old_lines(hunk_content)
        self.new_lines: list[Line] = self.__parse_new_lines(hunk_content)
        self.old_text = self.__parse_old_text()
        self.new_text = self.__parse_new_text()


        self.old_start: int = self.head.old_start
        self.old_len: int = self.head.old_len
        self.old_end: int = self.head.old_end
        self.new_start: int = self.head.new_start
        self.new_len: int = self.head.new_len
        self.new_end: int = self.head.new_end

    def __parse_head(self, hunk_content):
        diff_head_regex = re.compile(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@")
        head_line = hunk_content.split("\n")[0]
        match = diff_head_regex.search(head_line)
        if match:
            old_start = int(match.group(1))
            old_len = int(match.group(2))
            new_start = int(match.group(3))
            new_len = int(match.group(4))
            return Head(old_start=old_start,
                        old_len=old_len,
                        old_end=old_start+old_len-1,
                        new_start=new_start,
                        new_len=new_len,
                        new_end=new_start+new_len-1
                   )
        else:
            raise Exception

    def __parse_content_wo_head(self, hunk_content):
        content = []
        diff_head_regex = re.compile(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@")
        for line in hunk_content.split("\n"):
            if not diff_head_regex.search(line):
                content.append(line)
        return "\n".join(content)


    def __parse_old_lines(self, hunk_content):
        hunk_content_wo_head = self.__parse_content_wo_head(hunk_content)

        # loop var
        lines = []
        old_count = self.head.old_start
        for line in hunk_content_wo_head.split("\n"):
            if line.startswith("-"):
                lines.append(Line(
                    type="removed",
                    line_content=line[1:],  # 去掉减号
                    index=old_count,
                ))
                old_count += 1
            elif line.startswith("+"):
                pass
            else:
                lines.append(Line(
                    type="context",
                    line_content=line,
                    index=old_count,
                ))
                old_count += 1
        return lines

    def __parse_new_lines(self, hunk_content):
        hunk_content_wo_head = self.__parse_content_wo_head(hunk_content)

        # loop var
        lines = []
        new_count = self.head.new_start
        for line in hunk_content_wo_head.split("\n"):
            if line.startswith("-"):
                pass
            elif line.startswith("+"):
                lines.append(Line(
                    type="added",
                    line_content=line[1:],  # 去掉加号
                    index=new_count,
                ))
                new_count += 1
            else:
                lines.append(Line(
                    type="context",
                    line_content=line,
                    index=new_count,
                ))
                new_count += 1
        return lines

    def __parse_old_text(self):
        text = []
        for line in self.old_lines:
            text.append(line.line_content)
        return "\n".join(text)

    def __parse_new_text(self):
        text = []
        for line in self.new_lines:
            text.append(line.line_content)
        return "\n".join(text)



    def __str__(self):
        dec = "=" * 20
        old_title = dec + "old hunk" + dec + "\n"*2
        new_title = dec + "new hunk" + dec + "\n"*2
        return ("%"*20 + "   DIFF HUNK   " + "%"*20 + "\n"
                + str(self.head) + "\n" * 2
                + old_title
                + f"[= start: {self.head.old_start}, len: {self.head.old_len}, end: {self.head.old_end} =] \n"
                + "\n".join([str(line) for line in self.old_lines]) + "\n"*2
                + new_title
                + f"[= start: {self.head.new_start}, len: {self.head.new_len}, end: {self.head.new_end} =] \n"
                + "\n".join([str(line) for line in self.new_lines])
                + "\n"*3 )




class Diff:
    """
    a diff file
    iterface:
        hunks(iterable)
        heads(iterable)
    """
    def __init__(self, diff_content):
       self.hunks: list[Hunk] = self.__parse_hunks(diff_content)
       self.heads: list[Head] = self.__parse_heads(diff_content)

    def __parse_hunks(self, diff_content):
        # loop: find all diff_heads' index
        # loop vars
        diff_head_regex = re.compile(r"@@ -\d+,\d+ \+\d+,\d+ @@")
        line_indexes = []
        lines = diff_content.split("\n")
        for i, line in enumerate(lines):
            if diff_head_regex.search(line):
                line_indexes.append(i)
        # loop return:
        # line_indexes: list[int]
        # lines: list of diff lines

        # loop: split hunk by indexes
        # loop vars
        chunks = []
        right = len(diff_content.split("\n"))
        for index in reversed(line_indexes):
            chunks.append(Hunk("\n".join(lines[index:right])))
            right = index
        return chunks


    def __parse_heads(self, diff_content):
        diff_head_regex = re.compile(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@")
        res = re.findall(diff_head_regex, diff_content)

        # loop var
        heads = []
        for old_start, old_len, new_start, new_len in res:
            old_start = int(old_start)
            old_len = int(old_len)
            new_start = int(new_start)
            new_len = int(new_len)
            heads.append(
                Head(old_start=old_start,
                     old_len=old_len,
                     old_end=old_start+old_len-1,
                     new_start=new_start,
                     new_len=new_len,
                     new_end=new_start+new_len-1
                )
            )
        return heads



    @classmethod
    def from_file(cls, path: str):
        with open(path, "r") as diff:
            return cls(diff.read())

    @classmethod
    def from_str(cls, content: str):
        return cls(content)

    def __str__(self):
        return ("$&"*10+"   DIFF FILE   "+"$&"*10 + "\n"
                +f"{" "*20}   {str(len(self.heads)): ^3} HUNKS   {" "*20}" + "\n"
                +"\n".join([str(line) for line in self.hunks]))




