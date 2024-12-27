import tree_sitter
from tree_sitter import Language, Parser
from abc import ABC, abstractmethod
from typing import Literal, Callable
import time
from enum import IntEnum
from functools import wraps
from dataclasses import dataclass, asdict
from functools import partial


"""usecase
ast = AST(code)
node = debug(ast.query(By.SExpression, \"""
(function_definition
    (compound_statement) @statements)
\""")["statements"][0])
debug(ast.query(By.Type, "identifier", nest=True))
debug(ast.query(By.Type, "identifier", layer=6))
debug(ast.query(By.Types, ["identifier", "primitive_type"]))
debug(ast.query(By.Types, ["identifier", "primitive_type"], depth=3))
debug(ast.query(By.All))
debug(ast.query(By.Predicate, lambda node: node.type == "identifier"))
debug(ast.query(By.FuzzyType, "function"))
debug(ast.query(By.FuzzyType, "function", layer=2))
node = ast.query(By.FuzzyType, "function", nest=True)[0]
debug(ast.query(By.Type, "identifier", node=node))
"""



def text(node: tree_sitter.Node or list[tree_sitter.Node] or dict[str: list[tree_sitter.Node]]):
    if isinstance(node, list):
        text_list = []
        for n in node:
            text_list.append(n.text.decode("utf-8"))
        return text_list
    if isinstance(node, dict):
        text_dict = {}
        for k, li in node.items():
            text_li = []
            for node in li:
                text_li.append(node.text.decode("utf-8"))
            text_dict[k] = text_li
        return text_dict
    elif node is None:
        return None
    else:
        return node.text.decode("utf-8")


def debug(instance):
    print("="*30 + "\n" + text(instance) + "\n" + "-"*30 + "\n")
    return instance


def row(node: tree_sitter.Node or list[tree_sitter.Node]):
    if isinstance(node, list):
        line_list = []
        for n in node:
            line_list.append((n.start_point.row, n.end_point.row))
    else:
        return node.start_point.row, node.end_point.row


def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        res = func(*args, **kwargs)
        end = time.time()
        print(f'{func.__name__:<30} cost time: {end - start:.2f}s')
        return res
    return wrapper


class By(IntEnum):
    Type = 0            # ok
    Types = 1           # ok
    Predicate = 2       # ok
    All = 3             # ok
    FuzzyType = 4       # ok
    TypePath = 5
    SExpression = 6
    # LeafType = 7

# class QRange(IntEnum):


class Preprocessing:
    @abstractmethod
    def preprocess(self, code):
        pass


class Raw(Preprocessing):
    def preprocess(self, code):
        return code


class AST:
    """
    提供创建, 和各种AST的遍历方法和修改方法
    """

    def __init__(self, code, lang="cpp", preprocessor: Preprocessing=Raw):
        self.lang_str = lang
        self.parser, self.lang = self.__get_parser(lang)
        self.__update_ast(code, preprocessor)


    def __update_ast(self, code: bytes or str, preprocessor: Preprocessing=Raw):
        if isinstance(code, bytes):
            self.code_bytes = code
            code = code.decode("utf-8")
        if isinstance(code, str):
            self.code_bytes = code.encode("utf-8")

        self.preprocessor = preprocessor()
        self.code = self.preprocessor.preprocess(code)
        self.ast = self.parser.parse(self.code_bytes)
        self.root_node = self.ast.root_node


    def __get_parser(self, lang: str):
        match lang:
            case "cpp":
                import tree_sitter_cpp as tscpp
                lang = Language(tscpp.language())
                return Parser(lang), lang
            case _:
                raise NotImplemented

    find = False

    def preorder(self, do: Callable, node: tree_sitter.Node = None, nest=False, leaf=False):
        """
        param: do: 输入为Node的函数, 对节点执行操作
        param: node: 从哪个节点开始遍历, 若Node=None则从根节点开始遍历
        param: nest: 需要与do配合使用, 如果do返回值为真则停止遍历
        """
        def order(do, node, nest):
            if node is None:
                node = self.root_node

            if nest and self.find:
                return
            # Apply the function to the current node
            if not leaf or (leaf and len(node.children) == 0):
                self.find = do(node)
            # Recursively visit child nodes
            for child in node.children:
                order(do, child, nest=nest)
        order(do, node, nest)
        self.find = False

    def levelorder(self, do: Callable, depth: int = None, layer: int = None,
                   allover: bool = False, node: tree_sitter.Node = None, nest=False):
        """
        param: do: 对节点执行操作
        param: depth: BFS深度, 如果allover为True则参数失效
        param: allover: 是否完整遍历
        param: node: 从哪个节点开始遍历, 若Node=None则从根节点开始遍历
        param: layer: 只返回某层的节点, 和depth不能同时出现, 当allover为True时失效
        """
        if node is None:
            node = self.root_node

        # Initialize the queue for BFS
        queue = [(node, 0)]  # (node, current level)
        # result = []

        while queue:
            if nest and self.find:
                break
            current_node, current_layer = queue.pop(0)
            if allover:
                self.find = do(current_node)
                for child in current_node.children:
                    queue.append((child, current_layer + 1))
            elif depth is not None and layer is not None:
                raise Exception("参数layer和depth不能同时出现")
            elif depth is not None:
                if current_layer < depth:
                    self.find = do(current_node)
                    for child in current_node.children:
                        queue.append((child, current_layer + 1))
                elif current_layer == depth:
                    self.find = do(current_node)
            elif layer is not None:
                if current_layer < layer:
                    for child in current_node.children:
                        queue.append((child, current_layer + 1))
                elif current_layer == layer:
                    self.find = do(current_node)
        self.find = False

    @dataclass
    class __DFSParam:
        by_param: any
        node: tree_sitter.Node
        nest: bool
        leaf: bool

    @dataclass
    class __BFSParam:
        by_param: any
        node: tree_sitter.Node
        nest: bool
        leaf: bool
        depth: int
        layer: int

    def query(self, by: By, by_param: str or list[str] or Callable[[tree_sitter.Node], bool] = None,
              node: tree_sitter.Node=None, nest=False, depth: int = None, layer: int = None, leaf: bool = False):
        """
        范围参数:
        node, nest, depth, layer, leaf
        leaf, depth, layer只能有一个存在, 互不相容
        条件参数:
        by, by_param
        """

        if node is None:
            node = self.root_node
        match by:
            case By.Type:
                if depth or layer:
                    return self.__query_by_type_BFS(type_string=by_param, node=node, nest=nest, depth=depth, layer=layer)
                else:
                    return self.__query_by_type_DFS(type_string=by_param, node=node, nest=nest)

            case By.Types:
                if depth or layer:
                    return self.__query_by_types_BFS(type_list=by_param, node=node, nest=nest, depth=depth, layer=layer)
                else:
                    return self.__query_by_types_DFS(type_list=by_param, node=node, nest=nest)

            case By.All:
                if depth or layer:
                    return self.__query_by_all_BFS(node, depth, layer)
                else:
                    return self.__query_by_all_DFS(node)

            case By.TypePath:
                raise NotImplemented
                if depth or layer:
                    return self.__query_by_type_path_BFS()
                else:
                    return self.__query_by_type_path_DFS()

            case By.Predicate:
                if depth or layer:
                    return self.__query_by_predicate_BFS(predicate=by_param, node=node, nest=nest, depth=depth, layer=layer)
                else:
                    return self.__query_by_predicate_DFS(predicate=by_param, node=node, nest=nest)

            case By.FuzzyType:
                return self.query(by=By.Predicate, by_param=lambda node: by_param in node.type, node=node, nest=nest, depth=depth, layer=layer)

            case By.SExpression:
                query = self.lang.query(by_param)
                return query.captures(self.root_node)


    def __query_by_type_DFS(self, type_string: str, node: tree_sitter.Node=None, nest=False):
        res = []
        def do(node: tree_sitter.Node):
            if node.type == type_string:
                res.append(node)
                if nest:
                    return True
        self.preorder(do, node, nest)
        return res

    def __query_by_type_BFS(self, type_string: str,
              node: tree_sitter.Node=None, nest=False, depth: int = None, layer: int = None):
        res = []
        def do(node: tree_sitter.Node):
            if node.type == type_string:
                res.append(node)
                if nest:
                    return True
        if depth or layer:
            self.levelorder(do, depth, layer, False, node, nest)
        else:
            self.levelorder(do, None, None, True, node, nest)
        return res

    def __query_by_types_BFS(self, type_list: list[str], node: tree_sitter.Node=None, nest=False, depth: int = None, layer: int = None):
        res = {}
        for type in type_list:
            type_res = []
            def do(node: tree_sitter.Node):
                if node.type == type:
                    type_res.append(node)
                    if nest:
                        return True

            if depth or layer:
                self.levelorder(do, depth, layer, False, node, nest)
            else:
                self.levelorder(do, None, None, True, node, nest)
            res[type] = type_res
        return res


    def __query_by_types_DFS(self, type_list: list[str], node, nest):
        res = {}
        for type in type_list:
            type_res = []

            def do(node: tree_sitter.Node):
                if node.type == type:
                    type_res.append(node)
                    if nest:
                        return True

            self.preorder(do, node)
            res[type] = type_res
        return res

    def __query_by_all_DFS(self, node: tree_sitter.Node):
        if node is None:
            node = self.root_node
        res = []
        def do(node: tree_sitter.Node):
            res.append(node)
        self.preorder(do, node)
        return res


    def __query_by_all_BFS(self, node, depth: int, layer: int):
        if node is None:
            node = self.root_node
        res = []
        def do(node: tree_sitter.Node):
            res.append(node)
        self.levelorder(do, depth, layer, allover=False, node=node)
        return res

    def __query_by_predicate_BFS(self, predicate: Callable[[tree_sitter.Node], bool], node: tree_sitter.Node, nest=False, depth: int = None, layer: int = None):
        res = []

        def do(node: tree_sitter.Node):
            if predicate(node):
                res.append(node)
                return True

        if depth or layer:
            self.levelorder(do, depth, layer, False, node, nest)
        else:
            self.levelorder(do, None, None, True, node, nest)
        return res

    def __query_by_predicate_DFS(self, predicate: Callable[[tree_sitter.Node], bool], node: tree_sitter.Node, nest=False):
        res = []

        def do(node: tree_sitter.Node):
            if predicate(node):
                res.append(node)
                return True

        self.preorder(do, node, nest)
        return res


    @classmethod
    def from_code(cls, code, lang="cpp"):
        return cls(code, lang)

    @classmethod
    def from_file(cls, path, lang="cpp"):
        with open(path, "r") as f:
            code = f.read()
        return cls(code, lang)






if __name__ == '__main__':
    code = """
int main() {
    int a = 0;
    return 0;
}
    """










