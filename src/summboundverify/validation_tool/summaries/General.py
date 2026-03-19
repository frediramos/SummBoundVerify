from angr import SimProcedure, SIM_PROCEDURES


class _debug(SimProcedure):
    def run(self, ptr):
        print('*Debug', end=' ')
        i = 0
        while True:
            if self.state.solver.symbolic(self.state.memory.load(ptr + i, 1)):
                char_code = 'sym'
            else:
                char_code = self.state.solver.eval(
                    self.state.memory.load(ptr + i, 1))

            print(char_code, end=' ')
            if char_code == 0:
                break
            i += 1
        print()
        return


class _puts(SimProcedure):
    def run(self, string):
        puts = SIM_PROCEDURES['libc']['puts']
        self.inline_call(puts, string)
        return


class _malloc(SimProcedure):
    def run(self, sim_size):
        return self.state.heap.malloc(sim_size)


class _free(SimProcedure):
    def run(self, ptr):
        self.state.heap.free(ptr)


class _calloc(SimProcedure):
    def run(self, sim_nmemb, sim_size):
        return self.state.heap.calloc(sim_nmemb, sim_size)


class _realloc(SimProcedure):
    def run(self, ptr, size):
        return self.state.heap.realloc(ptr, size)


summaries = [
    _debug,
    _puts,
    _malloc,
    _free,
    _calloc,
    _realloc
]
