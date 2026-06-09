type_defs = [
    '#define NULL ((void*)0)',
    '#define INT_SIZE (sizeof(int) * 8)',
    '#define LONG_SIZE (sizeof(long) * 8)',
    '#define CHAR_SIZE (sizeof(char) * 8)',
    '#define PTR_SIZE (sizeof(void*) * 8)',
    'typedef void* symbolic;',
    'typedef int state_t;',
    'typedef unsigned int size_t;',
    'typedef unsigned int cnstr_t;',
    'typedef unsigned int result_t;',
    ''  # Hacky '\n'
]

validation_api = {
    'save_current_state':       'state_t save_current_state() {return 0;}',
    'get_cnstr':                'cnstr_t get_cnstr(symbolic var, size_t size) {return 0;}',
    'store_cnstr':              'void store_cnstr(char* name, cnstr_t constraint) {return;}',
    'halt_all':                 'void halt_all(state_t state) {return;}',
    'check_implications':       'result_t check_implications(char* constraint1, char* constraint2) {return 0;}',
    'print_counterexamples':    'void print_counterexamples(result_t result) {return;}',
    'sym_var_named':            'symbolic sym_var_named(char* name, size_t size) {return 0;}',
    'sym_var_array':            'symbolic sym_var_array(char* name, size_t index, size_t size) {return 0;}',
    'mem_addr':                 'void mem_addr(char* name, void* addr, size_t length) {return;}',
    '_ULE_':                    'cnstr_t _ULE_(symbolic var1, symbolic var2) {return 0;}',
    'is_sat':                   'int is_sat(cnstr_t cnstr) {return 0;}',
    'assume':                   'void assume(cnstr_t cnstr) {return;}'
}

standard_api = {
    'maximize':         'long maximize(symbolic sym_var){return 0;}',
    'minimize':         'long minimize(symbolic sym_var){return 0;}',
    'sym_var':          'symbolic sym_var(size_t size) {return 0;}',
    'is_symbolic':      'int is_symbolic(symbolic sym_var) {return 0;} ',
    'is_sat':           'int is_sat(cnstr_t cnstr) {return 0;}',
    'assume':           'void assume(cnstr_t cnstr) {return;}',
    'is_certain':       'int is_certain(cnstr_t cnstr){return 0;}',
    '_assert':          'void _assert(int expr){return;}',
    'push_pc':          'void push_pc(){return;}',
    'pop_pc':           'void pop_pc(){return;}',
}


constraints_api = {
    '_EQ_':     'cnstr_t _EQ_(symbolic var1, symbolic var2) {return 0;}',
    '_NEQ_':    'cnstr_t _NEQ_(symbolic var1, symbolic var2) {return 0;}',
    '_LT_':     'cnstr_t _LT_(symbolic var1, symbolic var2) {return 0;}',
    '_LE_':     'cnstr_t _LE_(symbolic var1, symbolic var2) {return 0;}',
    '_ULT_':    'cnstr_t _ULT_(symbolic var1, symbolic var2) {return 0;}',
    '_ULE_':    'cnstr_t _ULE_(symbolic var1, symbolic var2) {return 0;}',
    '_GT_':     'cnstr_t _GT_(symbolic var1, symbolic var2) {return 0;}',
    '_GE_':     'cnstr_t _GE_(symbolic var1, symbolic var2) {return 0;}',
    '_UGT_':    'cnstr_t _UGT_(symbolic var1, symbolic var2) {return 0;}',
    '_UGE_':    'cnstr_t _UGE_(symbolic var1, symbolic var2) {return 0;}',
    '_NOT_':    'cnstr_t _NOT_(cnstr_t cnstr) {return 0;}',
    '_OR_':     'cnstr_t _OR_(cnstr_t cnstr1, cnstr_t cnstr2) {return 0;}',
    '_AND_':    'cnstr_t _AND_(cnstr_t cnstr1, cnstr_t cnstr2) {return 0;}',
    '_ITE_':    'cnstr_t _ITE_(cnstr_t cnstr1, cnstr_t cnstr2, cnstr_t cnstr3) {return 0;}',
    '_ITE_VAR_': 'cnstr_t _ITE_VAR_(cnstr_t cnstr1, symbolic var1, symbolic var2) {return 0;}'
}

complete_api = validation_api | standard_api | constraints_api
