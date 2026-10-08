import claripy

from abc import ABC, abstractmethod

from angr.errors import SimValueError
from claripy.ast.bv import BV as BitVector

from summboundverify.exceptions import (
    SymbolicPointerError,
    InvalidIteFileDescriptor
)

from summboundverify.validation_tool.se.api import CSummary, ValidationCTX
from summboundverify.validation_tool.se.api.utils import SymbString, called_by

from .fs import SymbolicFS


class FileSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    @property
    def fs(self) -> SymbolicFS:
        plugin = self.state.fs
        assert isinstance(plugin, SymbolicFS)
        return plugin

    @property
    def int_size(self):
        return self.state.arch.sizeof["int"]

    def _single_valued(self, v: BitVector):
        if not v.symbolic:
            return True
        try:
            self.state.solver.eval_one(v)
            return True
        except SimValueError:
            return False

    def _signed(self, v: int | BitVector):
        """`v` as a signed int, or `v` itself if it has more than one value
        (the FS then rejects it)"""
        if isinstance(v, int):
            return v
        assert isinstance(v, BitVector)
        if not self._single_valued(v):
            return v
        value = self.state.solver.eval_one(v, cast_to=int)
        bits = v.size()
        return value - (1 << bits) if value >> (bits - 1) else value

    def ssize_t(self, v: BitVector):
        """`v` as an ssize_t: sign-extended to the architecture's width, so
        a -1 stays -1 once the caller reads all of it"""
        return claripy.SignExt(self.state.arch.bits - v.size(), v)

    def load_numeric(self, v: BitVector):
        if not self.is_symbolic(v):
            return self.state.solver.eval(v)
        return v

    def load_int(self, v: BitVector):
        assert isinstance(v, BitVector)
        size = self.int_size
        if v.size() > size:
            v = claripy.Extract(size - 1, 0, v)
        return v

    def load_string(self, addr, include_null: bool = False) -> SymbString:
        if self.is_symbolic(addr):
            caller = called_by(1)
            raise SymbolicPointerError(caller, addr)
        return super().load_string(addr, include_null)

    def unfold_read_fds(self, ite, invalid=-1):
        cases = list(claripy.reverse_ite_cases(ite))

        # Fds are either concrete or have the form: ite(cond, fd, invalid)
        if len(cases) == 1:
            return cases

        if not all(self._single_valued(v) for _, v in cases):
            raise InvalidIteFileDescriptor(ite)

        if not any(self._signed(v) == invalid for _, v in cases):
            raise InvalidIteFileDescriptor(ite)

        return cases

    def unfold_write_fds(self, ite, invalid=-1):
        cases = list(claripy.reverse_ite_cases(ite))

        # Fds are either concrete or have the form: ite(cond, fd, invalid)
        if len(cases) == 1:
            return cases

        if len(cases) > 2:
            raise InvalidIteFileDescriptor(ite)

        if not all(self._single_valued(v) for _, v in cases):
            raise InvalidIteFileDescriptor(ite)

        if not any(self._signed(v) == invalid for _, v in cases):
            raise InvalidIteFileDescriptor(ite)

        return cases

    def _call_fds(self, func, unfold, ite, args, signed=True, default=-1, invalid=-1):
        default = claripy.BVV(default, self.int_size)
        cases = unfold(ite, invalid)
        ret = [
            (cond, func(self._signed(v) if signed else v, *args))
            for cond, v in cases
        ]
        return claripy.ite_cases(ret, default)

    def call_read_op_fds(self, func, ite, *args, signed=True, default=-1, invalid=-1):
        return self._call_fds(
            func,
            self.unfold_read_fds,
            ite,
            args,
            signed,
            default,
            invalid,
        )

    def call_write_op_fds(self, func, ite, *args, signed=True, default=-1, invalid=-1):
        return self._call_fds(
            func,
            self.unfold_write_fds,
            ite,
            args,
            signed,
            default,
            invalid,
        )

    def call_fds_nested(self, func, ite1, ite2, *args, signed=True, default=-1):
        default = claripy.BVV(default, self.int_size)
        cases1 = self.unfold_write_fds(ite1)
        cases2 = self.unfold_write_fds(ite2)

        ret_cases = []
        for cond1, v1 in cases1:
            for cond2, v2 in cases2:
                v1 = self._signed(v1) if signed else v1
                v2 = self._signed(v2) if signed else v2
                ret = func(v1, v2, *args)
                cond = claripy.And(cond1, cond2)
                ret_cases.append((cond, ret))

        return claripy.ite_cases(ret_cases, default)

    @abstractmethod
    def run(self):
        pass


class file_create(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr, include_null=True)
        status = self.fs.create_file(filename)
        return status


class file_delete(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr, include_null=True)
        status = self.fs.delete_file(filename)
        return status


class file_exists(FileSummary):
    def run(self, filename_addr):
        filename = self.load_string(filename_addr, include_null=True)
        status = self.fs.exists_file(filename)
        return status


class file_open(FileSummary):
    def run(self, filename_addr, flags_addr):
        filename = self.load_string(filename_addr, include_null=True)
        flags = self.load_string(flags_addr)
        status = self.fs.open_file(filename, flags)
        return status


class file_close(FileSummary):
    def run(self, fd_bv):
        fd = self.load_int(fd_bv)
        f = self.fs.close_file
        status = self.call_write_op_fds(f, fd)
        return status


class file_write(FileSummary):
    def run(self, fd_bv, buffer_addr, count_bv):
        fd = self.load_int(fd_bv)
        buffer = self.load_string(buffer_addr, include_null=True)
        count = self.load_numeric(count_bv)
        f = self.fs.write_file
        n = self.call_write_op_fds(f, fd, buffer, count)
        return self.ssize_t(n)


class file_read(FileSummary):
    def run(self, fd_bv, buffer, count_bv):
        fd = self.load_int(fd_bv)
        count = self.load_numeric(count_bv)
        f = self.fs.read_file
        n = self.call_write_op_fds(f, fd, buffer, count)
        return self.ssize_t(n)


class FILE_from_fd(FileSummary):
    def run(self, fd_bv):
        fd = self.load_int(fd_bv)
        f = self.fs.FILE_from_fd
        fp = self.call_read_op_fds(f, fd, default=0)
        return fp


class fd_from_FILE(FileSummary):
    def run(self, fp_bv):
        fp = self.load_int(fp_bv)
        f = self.fs.fd_from_FILE
        fd = self.call_read_op_fds(f, fp, signed=False, invalid=0)
        return fd


class file_offset(FileSummary):
    def run(self, fd_bv):
        fd = self.load_int(fd_bv)
        f = self.fs.file_offset
        offset = self.call_read_op_fds(f, fd)
        return self.ssize_t(offset)


class file_set_offset(FileSummary):
    def run(self, fd_bv, offset_bv):
        fd = self.load_int(fd_bv)
        offset = self.load_numeric(offset_bv)
        f = self.fs.file_set_offset
        offset = self.call_write_op_fds(f, fd, offset)
        return self.ssize_t(offset)


class file_size(FileSummary):
    def run(self, fd_bv):
        fd = self.load_int(fd_bv)
        f = self.fs.file_size
        offset = self.call_read_op_fds(f, fd)
        return self.ssize_t(offset)


class file_set_size(FileSummary):
    def run(self, fd_bv, size_bv):
        fd = self.load_int(fd_bv)
        size = self.load_numeric(size_bv)
        f = self.fs.file_set_size
        size = self.call_write_op_fds(f, fd, size)
        return self.ssize_t(size)


class file_dup(FileSummary):
    def run(self, fd_bv):
        fd1 = self.load_int(fd_bv)
        f = self.fs.file_dup
        fd2 = self.call_write_op_fds(f, fd1)
        return fd2


class file_dup2(FileSummary):
    def run(self, fd1_bv, fd2_bv):
        fd1 = self.load_int(fd1_bv)
        fd2 = self.load_int(fd2_bv)
        f = self.fs.file_dup2
        ret = self.call_fds_nested(f, fd1, fd2)
        return ret


class file_mode(FileSummary):
    def run(self, fd_bv, mode_ptr_bv):
        fd = self.load_int(fd_bv)
        mode_ptr = self.load_numeric(mode_ptr_bv)
        f = self.fs.file_mode
        status = self.call_write_op_fds(f, fd, mode_ptr)
        return status


class file_set_mode(FileSummary):
    def run(self, fd_bv, mode_bv):
        fd = self.load_int(fd_bv)
        mode = self.load_numeric(mode_bv)
        f = self.fs.file_set_mode
        status = self.call_write_op_fds(f, fd, mode)
        return status


class file_flags(FileSummary):
    def run(self, fd_bv):
        fd = self.load_int(fd_bv)
        f = self.fs.file_flags
        flags = self.call_read_op_fds(f, fd)
        return flags


class fs_to_constraint(FileSummary):
    def run(self):
        c = self.fs.to_constraint()
        print(self.fs)
        print(f"lifted fs: {c}")
