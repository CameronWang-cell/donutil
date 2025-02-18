from typing import Literal

import tree_sitter

from astq import *
from func import *


# class Class:
#     def __init__(self, node: tree_sitter.Node, name, methods, fields):
#         self.node: tree_sitter.Node = node
#         self.name: str = name
#         self.methods: list[Function] = methods
#         self.fields: list[Variable] = fields




# class Variable:
#     def __init__(self, node: tree_sitter.Node):
#         pass

class OldNewFile:
    def __init__(self, code: str, type: Literal["OLD", "NEW"], filename: str = None):
        self.type = type
        self.ast = AST(code)
        self.filename = filename
        self.functions: list[Function] = self.__parse_functions()
        node = self.ast.root_node
        self.range = (node.range.start_point.row, node.range.end_point.row)
        # self.classes: list[Class] = self.__parse_classes()
        # self.global_variable: Variable = self.__parse_global_variable()


    def __parse_functions(self):
        func_SExpression = """
        (function_definition
        	type: (_)
   	        (function_declarator
    	        declarator: (_) 
                (parameter_list)
            )
            body: (_)
        ) @func_node
        """
        query_res = self.ast.query(By.SExpression, func_SExpression)
        function_list: list[Function] = []
        for func_node in query_res["func_node"]:
            function_list.append(Function.from_str(text(func_node)))
        return function_list

    def __str__(self):
        ret_str = "%"*30 + "\n"
        ret_str += f"[ filename ] {self.filename}\n"
        ret_str += f"[ type ] {self.type}\n"
        ret_str += f"[ range ] {self.range}\n"
        ret_str += "="*30 + f"\n[ functions ] {len(self.functions)} functions \n"
        for function in self.functions:
            ret_str += f"{function.func_name}\n"
        return ret_str + "\n" + "%"*30


    # def __parse_global_variable(self):
    #     return self.ast.query(By.Type, "declaration", layer=1)
    #
    # def __parse_classes(self):
    #     query_res = self.ast.query(By.SExpression, """
    #     (class_specifier
	#         name: (_) @class_name
	#         body: (_) @body
    #     ) @class
    #     """)
    #     print(query_res)
    #     class_list: list[Class] = []
    #     for class_node, class_name, body in zip(*query_res.values()):
    #         body_query_res = self.ast.query(By.Types, ["field_declaration", "function_definition"], layer=1, node=body)
    #         class_list.append(Class(class_node, text(class_name), body_query_res["field_declaration"], body_query_res["function_definition"]))
    #     return class_list



if __name__ == "__main__":
    code = """
SSU SYSCALL_DEFINE1(setfsuid, uid_t, uid)
{
	const struct cred *old;
	struct cred *new;
	uid_t old_fsuid;
	kuid_t kuid;

	old = current_cred();
    old_fsuid = kuid + 1;
	old_fsuid = from_kuid_munged(old->user_ns, old->fsuid);

	kuid = make_kuid(old->user_ns, uid);
	if (!uid_valid(kuid))
		return old_fsuid;

	new = prepare_creds();
	if (!new)
		return old_fsuid;

	if (uid_eq(kuid, old->uid)  || uid_eq(kuid, old->euid)  ||
	    uid_eq(kuid, old->suid) || uid_eq(kuid, old->fsuid) ||
	    nsown_capable(CAP_SETUID)) {
		if (!uid_eq(kuid, old->fsuid)) {
			new->fsuid = kuid;
			if (security_task_fix_setuid(new, old, LSM_SETID_FS) == 0)
				goto change_okay;
		}
	}
    
    for (int a = 0; a < 10; a++) {
    	break;
    }

	abort_creds(new);
	return old_fsuid;

change_okay:
	commit_creds(new);
	return old_fsuid;
}
    """

    file = OldNewFile(code, type="OLD")
    print(file.functions[0].code)

