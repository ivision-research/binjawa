from wasamole.core.instructions import disassemble_instruction, Opcode


def compute_branch_map(module):
    branch_map = {}

    for function in module.functions:
        branches_to_resolve = []
        else_stack = []
        addr = function.address
        last_instr_addr = addr + function.size - 1
        label_stack = [(Opcode.BLOCK, 0)]
        prev_addr = 0

        for instr in function.instructions:
            opcode = instr.opcode
            if opcode in (Opcode.BLOCK, Opcode.LOOP, Opcode.IF):
                label_stack.append((opcode, addr))
            elif opcode in (Opcode.BR, Opcode.BR_IF):
                label_index = instr.operands[0].index
                stack_index = -(label_index + 1)
                if label_stack[stack_index][0] == Opcode.LOOP:
                    branch_map[addr] = label_stack[stack_index][1]
                elif label_stack[stack_index][0] in (Opcode.BLOCK, Opcode.IF):
                    branches_to_resolve.append((addr, label_index))
            elif opcode == Opcode.ELSE:
                assert label_stack[-1][0] == Opcode.IF
                branch_map[label_stack[-1][1]] = addr
                else_stack.append(prev_addr)
                label_stack.append((opcode, addr))
            elif opcode == Opcode.END:
                if len(label_stack):
                    source_addr = label_stack[-1][1]
                    if label_stack[-1][0] == Opcode.ELSE:
                        branch_map[else_stack.pop()] = addr + instr.size
                        # Extra pop for the IF.
                        label_stack.pop()
                    elif label_stack[-1][0] == Opcode.IF:
                        branch_map[source_addr] = addr + instr.size

                    # Resolve any outstanding branches.
                    new_branch_set = []
                    for branch_i in range(len(branches_to_resolve)):
                        source_addr, label_index = branches_to_resolve[branch_i]
                        if label_index == 0:
                            branch_map[source_addr] = addr
                        else:
                            new_branch_set.append((source_addr, label_index - 1))
                    if len(new_branch_set):
                        branches_to_resolve = new_branch_set

                    label_stack.pop()
                    if not len(label_stack):
                        branch_map[addr] = None
            prev_addr = addr
            addr += instr.size

    return branch_map
