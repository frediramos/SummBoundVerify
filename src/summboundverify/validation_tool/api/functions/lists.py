import claripy

from collections import deque
from abc import ABC, abstractmethod

from claripy.ast.bv import BV as BitVector
from angr.state_plugins.sim_action_object import SimActionObject

from ..summary import CSummary
from ..context import ValidationCTX


class ListSummary(CSummary, ABC):
    def __init__(self, ctx: ValidationCTX):
        super().__init__(ctx)

    def increment_LC(self):
        current = self.ctx.LIST_COUNTER
        self.ctx.LIST_COUNTER += 1
        return current

    def _new_lst(self, init=None):
        if not init:
            init = []
        retval = self.increment_LC()
        self.ctx.LIST_MAP.append(deque(init))
        return retval

    def _lst_tail(self, lst: deque):
        tail = deque(lst)
        tail.popleft()
        return self._new_lst(tail)

    def _lst_head(self, lst: deque):
        return lst[0]

    def _lst_prepend(self, c, lst: deque):
        if isinstance(c, SimActionObject):
            c = c.to_claripy()
        lst.appendleft(c)

    def _lst_append(self, c, lst: deque):
        if isinstance(c, SimActionObject):
            c = c.to_claripy()
        lst.append(c)

    def _lst_from_id(self, lst_id: int | BitVector):
        if isinstance(lst_id, BitVector):
            lst_id = self.state.solver.eval(lst_id)
        return self.ctx.LIST_MAP[lst_id]

    def _lst_extract_SAO(self, lst):
        if isinstance(lst, SimActionObject):
            lst = lst.to_claripy()
        if isinstance(lst, BitVector) and lst.op == 'Concat':
            lst = lst.args[1]
        assert isinstance(lst, BitVector)
        return lst

    def _lst_is_ite(self, lst):
        if isinstance(lst, BitVector):
            return lst.op == 'If'
        else:
            assert isinstance(lst, int)
            return False

    def _lst_is_empty(self, lst):
        lst = self._lst_extract_SAO(lst)
        if self._lst_is_ite(lst):
            reverse = claripy.reverse_ite_cases(lst)
            expr_list = []
            for case in reverse:
                c, l = case
                expr = claripy.And(c, self._lst_is_empty(l))
                expr_list.append(expr)
            ret_expr = claripy.Or(*expr_list)
            return ret_expr
        else:
            lst = self._lst_from_id(lst)
            return not bool(lst)

    @abstractmethod
    def run(self):
        pass


class lst_mk(ListSummary):

    def run(self):
        return self._new_lst()


class lst_cons(ListSummary):

    def run(self, c, lst):
        lst = self._lst_extract_SAO(lst)

        if self._lst_is_ite(lst):
            reverse = claripy.reverse_ite_cases(lst)
            for case in reverse:
                _, lst_id = case
                inner_lst = self._lst_from_id(lst_id)
                self._lst_prepend(c, inner_lst)

            lst = lst.sign_extend(
                self.state.arch.bits -
                lst.length  # type: ignore
            )

            return lst
        else:
            lst_id = lst
            lst = self._lst_from_id(lst_id)
            self._lst_prepend(c, lst)
            return lst_id


class lst_empty(ListSummary):

    def run(self, lst):
        result = self._lst_is_empty(lst)
        if result is True:
            return self.ctx.TRUE
        elif result is False:
            return self.ctx.FALSE
        else:
            return_value = self.increment_CC()
            self.ctx.CNSTR_MAP.append(result)
            return return_value


class lst_tl(ListSummary):

    def run(self, lst):
        lst = self._lst_extract_SAO(lst)

        if self._lst_is_ite(lst):
            reverse = claripy.reverse_ite_cases(lst)
            expr_list = []

            for case in reverse:
                c, l = case

                if not self.is_sat(c):
                    continue

                l = self._lst_from_id(l)
                tail_l = self._lst_tail(l)
                tail_l = claripy.BVV(tail_l, self.state.arch.sizeof['int'])
                expr_list.append((c, tail_l))

            # [(a,b), (not(a),c)] -> ite(a, b, d)
            ret_expr = claripy.ite_cases(expr_list[:-1], expr_list[-1][1])

            ret_expr = ret_expr.sign_extend(
                self.state.arch.bits - ret_expr.length
            )

            return ret_expr

        else:
            lst = self._lst_from_id(lst)
            return self._lst_tail(lst)


class lst_hd(ListSummary):

    def run(self, lst):
        lst = self._lst_extract_SAO(lst)

        if self._lst_is_ite(lst):
            reverse = claripy.reverse_ite_cases(lst)
            expr_list = []

            for case in reverse:
                c, l = case
                if not self.is_sat(c):
                    continue

                l = self._lst_from_id(l)
                head = self._lst_head(l)
                expr_list.append((c, head))

            # [(a,b), (not(a),c)] -> ite(a, b, d)
            ret_expr = claripy.ite_cases(expr_list[:-1], expr_list[-1][1])

            ret_expr = ret_expr.sign_extend(
                self.state.arch.bits - ret_expr.length
            )
            return ret_expr
        else:
            lst = self._lst_from_id(lst)
            return self._lst_head(lst)


class lst_len(ListSummary):

    def lst_len(self, lst):
        lst = self._lst_extract_SAO(lst)

        if self._lst_is_ite(lst):
            reverse = claripy.reverse_ite_cases(lst)
            sizes = []

            for case in reverse:
                c, l = case
                if not self.is_sat(c):
                    continue

                l = self._lst_from_id(l)
                size = len(l)
                size = claripy.BVV(size, self.state.arch.sizeof['int'])
                sizes.append((c, size))

            # [(a,b), (not(a),c)] -> ite(a, b, d)
            ret_expr = claripy.ite_cases(sizes[:-1], sizes[-1][1])

            ret_expr = ret_expr.sign_extend(
                self.state.arch.bits - ret_expr.length
            )
            return ret_expr
        else:
            lst = self._lst_from_id(lst)
            return len(lst)


class lst_nbytes(ListSummary):

    def run(self, c, n):
        if isinstance(c, int):
            char = [claripy.BVV(c, self.state.arch.bits)]
        elif isinstance(c, bytes):
            char = [claripy.BVV(c)]
        else:
            assert isinstance(c, BitVector)
            char = [c]

        if self.is_symbolic(n):
            max_n = self.state.solver.max(n)

            cases = [
                (n == i, self._new_lst(i * char))
                for i in range(max_n) if self.is_sat(n == i)
            ]

            default = self._new_lst(max_n * char)
            default = claripy.BVV(default, self.state.arch.sizeof['int'])
            ret_expr = claripy.ite_cases(cases, default)

            ret_expr = ret_expr.sign_extend(
                self.state.arch.bits - ret_expr.length
            )
            return ret_expr
        else:
            return self._new_lst(n * char)


class lst_zeros(ListSummary):

    def run(self, n):
        helper = lst_nbytes(self.ctx)
        return helper.run(0, n)


class cond_write(ListSummary):

    def run(self, addr, c, pc_: BitVector):
        pc_id = self.state.solver.eval(pc_)
        pc = self.ctx.CNSTR_MAP[pc_id]

        if self.is_symbolic(addr):
            min_addr = self.state.solver.min(addr)
            max_addr = self.state.solver.max(addr)
            for _addr in range(min_addr, max_addr + 1):
                current = self.load(_addr)
                to_store = claripy.If(pc, c, current)
                to_store = claripy.If(addr == _addr, to_store, current)
                self.store(_addr, to_store)
            return
        else:
            current = self.load(addr)
            to_store = claripy.If(pc, c, current)
            self.store(addr, to_store)
            return
