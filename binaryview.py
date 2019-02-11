from binaryninja import *
from wasamole.io import from_bytes
from .branch_resolver import compute_branch_map

HEADER_SIZE = 8


class WASMView(BinaryView):
    name = "WASM"
    long_name = "WASM File"

    def __init__(self, data):
        BinaryView.__init__(self, parent_view=data, file_metadata=data.file)
        self.platform = Architecture["WASM"].standalone_platform
        self.raw = data

    @classmethod
    def is_valid_for_data(self, data):
        hdr = data.read(0, HEADER_SIZE)
        if len(hdr) < HEADER_SIZE:
            return False
        if hdr[0:4] != b"\x00asm":
            return False

        # Only version 1.0 for now.
        version = struct.unpack("<I", hdr[4:])[0]
        if version != 1:
            return False
        return True

    def init(self):
        file_size = len(self.raw)
        wasm_bytes = self.raw.read(0, file_size)
        wasm_module = from_bytes(wasm_bytes)
        # HACK: Currently there is no decent way to share information
        # between a `BinaryView` and an `Architecture` instance. See:
        #
        #   https://github.com/Vector35/binaryninja-api/issues/551
        #
        # We hack around that by placing the branch offset map on the
        # WASM architecture object.
        self.arch.current_branch_map = compute_branch_map(wasm_module)
        self.arch.current_module = wasm_module

        self.add_auto_segment(
            0,
            file_size,
            0,
            file_size,
            SegmentFlag.SegmentReadable
            | SegmentFlag.SegmentContainsData
            | SegmentFlag.SegmentContainsCode,
        )

        for function in wasm_module.functions:
            # Define code section for function body code.
            self.add_auto_section(
                f"code_{hex(function.address)}",
                function.address,
                function.size,
                SectionSemantics.ReadOnlyCodeSectionSemantics,
            )
            name = function.name if function.name else "func_" + str(function.address)
            self.define_auto_symbol(
                Symbol(SymbolType.FunctionSymbol, function.address, name)
            )
            self.add_function(function.address)

            # TODO: Process locals.

        return True

    def perform_is_executable(self):
        return True


WASMView.register()
