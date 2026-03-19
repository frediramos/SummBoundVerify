from angr import SimProcedure


class Assert(SimProcedure):

    def run(self, value):
        value = self.state.solver.eval(value)
        if value == 0:
            self.exit(0)
        else:
            self.ret()


HASH_COUNTER = 0


class hashmap_hash(SimProcedure):

    def run(self, _, maxHash):
        maxHash = self.state.solver.eval(maxHash)
        global HASH_COUNTER
        hash_value = HASH_COUNTER % (maxHash + 1)
        HASH_COUNTER += 1
        # print('hashmap_hash:',hash_value)
        self.ret(hash_value)


summaries = [
    Assert,
    hashmap_hash
]
