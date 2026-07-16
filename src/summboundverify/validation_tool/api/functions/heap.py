from abc import ABC, abstractmethod

from summboundverify.exceptions import MemoryPermissionsError

from ..summary import CSummary
from ..context import ValidationCTX


class HeapSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def is_writable(self, addr):
        perms = self.state.memory.permissions(addr)
        can_write = self.state.solver.is_true((perms & 2) != 0)
        return can_write

    def is_readable(self, addr):
        perms = self.state.memory.permissions(addr)
        can_write = self.state.solver.is_true((perms & 1) != 0)
        return can_write

    @abstractmethod
    def run(self):
        pass


class mem_alloc(HeapSummary):
    def run(self, size):
        size = self.state.solver.max(size)
        ptr = self.state.heap._malloc(size)  # type: ignore
        self.ctx.HEAP_CHUNKS[ptr] = size
        return ptr


class mem_free(HeapSummary):
    def run(self, ptr):
        self.state.heap._free(ptr)  # type: ignore
        del self.ctx.HEAP_CHUNKS[ptr]
        return


class n_allocd(HeapSummary):
    """
    Returns the number of bytes (allocated) pointed to by `ptr`
    **Needs** to be a mallocd heap pointer.
    """

    def run(self, ptr):
        return self.ctx.HEAP_CHUNKS[ptr]


class mallocd(HeapSummary):
    """
    Returns `True` if the pointer `ptr` was returned by `malloc`.
    """

    def run(self, ptr):
        return (ptr in self.ctx.HEAP_CHUNKS)


class is_rw(HeapSummary):
    """
    Raise if the memory pointed to by `ptr` does not have `r/w` permissions.
    Does **not** need to be a mallocd heap pointer.
    """

    def run(self, ptr, size):
        def is_rw(ptr):
            return self.is_readable(ptr) and self.is_writable(ptr)

        min_addr = self.state.solver.min(ptr)
        max_addr = self.state.solver.max(ptr)
        min_size = self.state.solver.min(size)
        max_size = self.state.solver.max(size)

        for addr in range(min_addr, max_addr + 1):
            for n in range(min_size, max_size + 1):
                addr_ = addr + n
                if not is_rw(addr_):
                    raise MemoryPermissionsError(addr_, ptr, size)
            return


class allocd(HeapSummary):
    """
    Alias of `is_rw`.
    (For backward compatibility)
    """

    def run(self, ptr, size):
        helper = is_rw(self.ctx)
        return helper.run(ptr, size)
