from binaryninja import *
from wasamole.core.instructions import (
    disassemble_instruction,
    Opcode,
    ZeroOperand,
    IndexOperand,
    IndexVectorOperand,
    I32Operand,
    I64Operand,
)


class WASM(Architecture):
    name = "WASM"

    # WASM doesn't actually have a stack pointer, but Binary Ninja
    # requires one to be defined.
    regs = {"sp": RegisterInfo("sp", 2)}
    stack_pointer = "sp"
    instr_alignment = 1
    # This still isn't large enough as some WASM instructions, like
    # `brtable`, can be an arbitrary length.
    max_instr_length = 256

    def __init__(self, *args, **kwargs):
        super(WASM, self).__init__(*args, **kwargs)
        self.m = None
        self.branch_map = None

    def get_instruction_info(self, data, addr):
        try:
            instr = disassemble_instruction(data)
        except Exception:
            return None

        i_info = InstructionInfo()
        i_info.length = instr.size
        opcode = instr.opcode
        branch_map = Architecture["WASM"].current_branch_map
        module = Architecture["WASM"].current_module

        def add_branch(branch_type, addr):
            i_info.add_branch(branch_type, addr)

        def add_long_branch(branch_type, addr):
            if addr in branch_map:
                add_branch(branch_type, branch_map[addr])

        if opcode == Opcode.CALL:
            add_branch(
                BranchType.CallDestination,
                module.functions[instr.operands[0].index].address,
            )
        elif opcode == Opcode.IF:
            add_long_branch(BranchType.FalseBranch, addr)
            add_branch(BranchType.TrueBranch, addr + i_info.length)
        elif opcode == Opcode.BR_IF:
            add_long_branch(BranchType.TrueBranch, addr)
            add_branch(BranchType.FalseBranch, addr + i_info.length)
        elif opcode == Opcode.RETURN:
            i_info.add_branch(BranchType.FunctionReturn)
        elif opcode == Opcode.END:
            if addr in branch_map:
                if branch_map[addr] == None:
                    i_info.add_branch(BranchType.FunctionReturn)
                else:
                    add_long_branch(BranchType.UnconditionalBranch, addr)
        else:
            add_long_branch(BranchType.UnconditionalBranch, addr)

        return i_info

    def get_instruction_text(self, data, addr):
        try:
            instr = disassemble_instruction(data)
        except Exception:
            return None
        module = Architecture["WASM"].current_module

        tokens = [
            InstructionTextToken(
                InstructionTextTokenType.InstructionToken, instr.opname
            )
        ]

        # TODO: The below code for processing operands is overly complicated and gross. Simplify.
        operand_count = 0
        for operand in instr.operands:
            if operand_count > 0:
                tokens.append(
                    InstructionTextToken(InstructionTextTokenType.TextToken, ", ")
                )
            else:
                tokens.append(
                    InstructionTextToken(InstructionTextTokenType.TextToken, " ")
                )

            if isinstance(operand, (ZeroOperand, I32Operand, I64Operand)):
                tokens.append(
                    InstructionTextToken(
                        InstructionTextTokenType.IntegerToken,
                        str(operand),
                        operand.value,
                    )
                )
            elif isinstance(operand, IndexOperand):
                if instr.opcode == Opcode.CALL:
                    function = module.functions[operand.index]
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.PossibleAddressToken,
                            function.name,
                            function.address,
                        )
                    )
                else:
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.IntegerToken,
                            str(operand),
                            operand.index,
                        )
                    )
            elif isinstance(operand, IndexVectorOperand):
                tokens.append(
                    InstructionTextToken(InstructionTextTokenType.TextToken, "[")
                )
                for index_i in range(len(operand.indices)):
                    index = operand.indices[index_i]
                    if index_i > 0:
                        tokens.append(
                            InstructionTextToken(
                                InstructionTextTokenType.TextToken, ", "
                            )
                        )
                    tokens.append(
                        InstructionTextToken(
                            InstructionTextTokenType.IntegerToken, str(index), index
                        )
                    )
                tokens.append(
                    InstructionTextToken(InstructionTextTokenType.TextToken, "]")
                )
            else:
                tokens.append(
                    InstructionTextToken(
                        InstructionTextTokenType.TextToken, str(operand)
                    )
                )
            operand_count += 1

        return tokens, instr.size

    def get_instruction_low_level_il(self, data, addr, il):
        # TODO: Implement?
        return None


WASM.register()
