import tree_sitter
from astq import *

from enum import IntEnum

# class StatementType(IntEnum):
#     Declaration = 0
#     Assignment = 1
#     Call = 2
#     Goto = 3
#     If = 4
#     For = 5
#     While = 6
#     Switch = 7
#     Return = 8
#     Break = 9
#
# class Statement:
#     def __init__(self, node: tree_sitter.Node, type: StatementType):
#         self.text = text(node)
#         self.type = type
#         self.range = (node.range.start_point.row, node.range.end_point.row)



class Function:
    def __init__(self, node: tree_sitter.Node,
                 return_type,
                 func_name,
                 parameter_list,
                 body,
                 global_ast=None
                 ):
        self.node: tree_sitter.Node = node
        self.range = (node.range.start_point.row, node.range.end_point.row)
        self.return_type: str = return_type
        self.func_name: str = func_name
        self.parameter_list: str = parameter_list
        self.body: tree_sitter.Node = body
        self.global_ast: AST = global_ast

    # def __parse_statements(self):
    #     statements_and_if_for =  self.global_ast.query(By.All, layer=1, node=self.body)
    #     statements = []
    #     for statement in statements_and_if_for:
    #         match statement.type:
    #             case "declaration":
    #                 statements.append(Statement(statement, type=StatementType.Declaration))
    #             case "expression_statement":
    #                 statements.append(Statement(statement, type=StatementType.Assignment))
    #             case "return_statement":
    #             case "if_statement" or "for_statement" or "labeld":

    @classmethod
    def from_str(cls, function_code: str):
        func_SExpression = """
                (function_definition
                	type: (_) @return_type
           	        (function_declarator
            	        declarator: (_) @func_name
                        (parameter_list) @parameter_list
                    )
                    body: (_) @body 
                )
                """
        func_ast = AST.from_code(function_code)
        res = func_ast.query(By.SExpression, func_SExpression)
        return Function(node=func_ast.root_node, return_type=text(res["return_type"][0]), func_name=text(res["func_name"][0]), parameter_list=text(res["parameter_list"][0]), body=text(res["body"][0]))



    def __str__(self):
        return "="*30 + "\n"\
            + f"[ range ] {self.range} \n[ return_type ] {self.return_type} \n[ func_name ] {self.func_name}\n[ parameter_list ] {self.parameter_list}\n\n[ function ]\n{text(self.node)}" + "\n" \
            + "="*30
