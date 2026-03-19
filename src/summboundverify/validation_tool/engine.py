#!/usr/bin/env python3
import traceback
import logging
import psutil
import signal
import time
import json
import sys
import os

from angr import Project, SimState, SimulationManager, SimProcedure, SimHeapPTMalloc
from angr import options, BP_AFTER

from .validationAPI import validation as Validation_API
from .validationAPI.constraints import summaries as constraints
from .validationAPI.solver import summaries as solver
from .validationAPI.validation import summaries as validation

from .utils import truncate, write2file, get_fnames, get_states
from .macros import SYM_VAR


class angrEngine():

    def __init__(self, binary: str, timeout=30*60, results_dir='.',
                 stats_dir=None, paths_dir=None,
                 convert_ascii=False,
                 ignore=None, debug=False, max_memory=None) -> None:

        self.binary = os.path.normpath(binary)
        self.timeout = timeout
        self.max_memory = max_memory

        self.results_dir = results_dir

        self.stats_dir = stats_dir
        self.paths_dir = paths_dir

        self.convert_ascii = convert_ascii
        self.ignore_list = self._ignore_list(ignore)

        self.binary_name = os.path.split(self.binary)[1]

        self.debug = debug

        self.fnames = get_fnames(self.binary)
        self.fcalled = {}

    def _ignore_list(self, ignore):
        if not ignore:
            return []
        with open(ignore, 'r') as f:
            implemented = f.readlines()
            return [f.strip() for f in implemented]

    # Hook API symbols
    def _set_hooks(self, p: Project, sm: SimulationManager):

        summaries = [*constraints, *solver, *validation]

        for s in summaries:
            p.hook_symbol(s.__name__, s())

        # Validation
        p.hook_symbol('halt_all', Validation_API.halt_all(sm))
        p.hook_symbol('print_counterexamples', Validation_API.print_counterexamples(
            sm, self.binary_name, self.results_dir, self.convert_ascii))

    def _create_entry_state(self, p: Project) -> SimState:

        opt = {options.TRACK_SOLVER_VARIABLES,
               options.ZERO_FILL_UNCONSTRAINED_MEMORY,
               options.ZERO_FILL_UNCONSTRAINED_REGISTERS}

        state = p.factory.entry_state(mode='symbolic', add_options=opt)

        if state.arch.bits == 64:
            heap = SimHeapPTMalloc(heap_base=0x0000000000000000)
        else:
            heap = SimHeapPTMalloc()
        state.register_plugin('heap', heap)

        state.libc.simple_strtok = False

        if self.stats_dir:
            state.inspect.b('call', when=BP_AFTER, action=self._count_fcall)

        return state

    def _register_timeout(self, sm: SimulationManager):

        def handler(signum, frame):
            if self.stats_dir:
                self._save_stats(sm, timeout=True)
            print(f'[!] Timeout Detected {self.timeout} seconds')
            sys.exit(0)

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(self.timeout)

    def _count_fcall(self, state):
        addr = str(state.inspect.function_address)  # <BV32 0x80483a3>
        addr = addr.split()[1]  # 0x80483a3>
        addr = addr[:-1]  # 0x80483a3
        # addr = addr[2:]							#80483a3

        symbol = state.project.loader.find_symbol(int(addr, 16))
        if not symbol:
            return

        if addr in self.fcalled.keys():
            self.fcalled[symbol.name] += 1
        else:
            self.fcalled[symbol.name] = 1

    def _save_paths(self, sm: SimulationManager):

        def filter_gen(var):
            if SYM_VAR in str(var):
                return True
            return False

        # Create results folder if it does not exist yet
        if not os.path.exists(self.paths_dir):
            os.makedirs(self.paths_dir)

        for idx, state in enumerate(get_states(sm)):
            file = f'{self.paths_dir}/{self.binary_name}_{idx}.path'
            truncate(file)

            vars = state.solver.all_variables
            vars = list(filter(filter_gen, vars))

            for var in vars:
                v = state.solver.eval(var)
                write2file(file, v)
        return

    def _save_stats(self, sm: SimulationManager,
                    time_spent=None, timeout=None,
                    start=None,
                    exception=None):

        out_stats = {}

        # Create results folder if it does not exist yet
        if not os.path.exists(self.stats_dir):
            os.makedirs(self.stats_dir)

        if exception:
            assert start is not None
            time_spent = round(time.time()-start, 4)
            out_stats['Exception'] = f'{type(exception)}:{exception}'

        elif timeout:
            out_stats['Time'] = f'Timeout:{timeout}'

        else:
            assert time_spent is not None
            out_stats['Time'] = time_spent

        if Validation_API.SUMM_PATHS:
            out_stats['N_Paths'] = {
                "summary": Validation_API.SUMM_PATHS,
                "concrete": Validation_API.CNCR_PATHS,
            }
        else:
            out_stats['N_Paths'] = len(get_states(sm))

        out_stats['Fcalled'] = self.fcalled
        out_stats['Fcalled'].pop('main', None)

        out_stats = {self.binary_name: out_stats}

        file = open(f'{self.stats_dir}/{self.binary_name}_stats.json', 'w')
        json_object = json.dumps(out_stats, indent=2)
        file.write(json_object)
        file.flush()
        file.close()

    def _step(self, sm: SimulationManager, start: float):
        try:
            while sm.active:
                sm.step()

                if self.max_memory:
                    if psutil.virtual_memory().percent > self.max_memory:
                        raise MemoryError

        except Exception as e:

            if self.stats_dir:
                self._save_stats(sm, exception=e, start=start)

            print(traceback.format_exc())
            sys.exit(1)

    def run(self):

        if self.debug:
            logging.getLogger('angr').setLevel('INFO')

        sys.setrecursionlimit(20000)

        p = Project(self.binary, exclude_sim_procedures_list=self.ignore_list)

        state = self._create_entry_state(p)
        sm = p.factory.simulation_manager(state)
        self._register_timeout(sm)

        self._set_hooks(p, sm)

        # Run Symbolic Execution
        start = time.time()
        self._step(sm, start)
        end = time.time()

        # Store execution time
        tspent = round(end-start, 4)

        if self.stats_dir:
            self._save_stats(sm, time_spent=tspent)

        if self.paths_dir:
            self._save_paths(sm)

        return
