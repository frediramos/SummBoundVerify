type_defs = [
    '#define NULL ((void*)0)\n'
    '#define INT_SIZE (sizeof(int) * 8)\n',
    '#define LONG_SIZE (sizeof(long) * 8)\n',
    '#define CHAR_SIZE (sizeof(char) * 8)\n',
    '#define PTR_SIZE (sizeof(void*) * 8)\n',
    'typedef void* symbolic;\n',
    'typedef int state_t;\n',
    'typedef unsigned int size_t;\n',
    'typedef unsigned int cnstr_t;\n',
    'typedef unsigned int result_t;\n',
    '\n'
]

validation_api = {
    'save_current_state':       'state_t save_current_state() {return 0;}\n',
    'get_cnstr':                'cnstr_t get_cnstr(symbolic var, size_t size) {return 0;}\n',
    'store_cnstr':              'void store_cnstr(char* name, cnstr_t constraint) {return;}\n',
    'halt_all':                 'void halt_all(state_t state) {return;}\n',
    'check_implications':       'result_t check_implications(char* constraint1, char* constraint2) {return 0;}\n',
    'print_counterexamples':    'void print_counterexamples(result_t result) {return;}\n',
    'sym_var_named':            'symbolic sym_var_named(char* name, size_t size) {return 0;}\n',
    'sym_var_array':            'symbolic sym_var_array(char* name, size_t index, size_t size) {return 0;}\n',
    'mem_addr':                 'void mem_addr(char* name, void* addr, size_t length) {return;}\n',
    '_ULE_':                    'cnstr_t _ULE_(symbolic var1, symbolic var2) {return 0;}\n',
    'assume':                   'void assume(cnstr_t cnstr) {return;}\n'
}

standard_api = {
    'maximize':         'long maximize(symbolic sym_var){return 0;}\n',
    'sym_var':          'symbolic sym_var(size_t size) {return 0;}\n',
    'is_symbolic':      'int is_symbolic(symbolic sym_var) {return 0;} \n',
    'is_sat':           'int is_sat(cnstr_t cnstr); \n',
    'assume':           'void assume(cnstr_t cnstr) {return;}\n',
    'is_certain':       'int is_certain(cnstr_t cnstr){return 0;}\n',
    '_assert':          'void _assert(int expr){return;}\n',
    'push_pc':          'void push_pc(){return;}\n',
    'pop_pc':           'void pop_pc(){return;}\n',
}


constraints_api = {
    '_EQ_':    'cnstr_t _EQ_(symbolic var1, symbolic var2) {return 0;}\n',
    '_NEQ_':    'cnstr_t _NEQ_(symbolic var1, symbolic var2) {return 0;}\n',
    '_LT_':    'cnstr_t _LT_(symbolic var1, symbolic var2) {return 0;}\n',
    '_LE_':    'cnstr_t _LE_(symbolic var1, symbolic var2) {return 0;}\n',
    '_ULT_':    'cnstr_t _ULT_(symbolic var1, symbolic var2) {return 0;}\n',
    '_ULE_':    'cnstr_t _ULE_(symbolic var1, symbolic var2) {return 0;}\n',
    '_GT_':    'cnstr_t _GT_(symbolic var1, symbolic var2) {return 0;}\n',
    '_GE_':    'cnstr_t _GE_(symbolic var1, symbolic var2) {return 0;}\n',
    '_UGT_':    'cnstr_t _UGT_(symbolic var1, symbolic var2) {return 0;}\n',
    '_UGE_':    'cnstr_t _UGE_(symbolic var1, symbolic var2) {return 0;}\n',
    '_NOT_':    'cnstr_t _NOT_(cnstr_t cnstr) {return 0;}\n',
    '_OR_':    'cnstr_t _OR_(cnstr_t cnstr1, cnstr_t cnstr2) {return 0;}\n',
    '_AND_':    'cnstr_t _AND_(cnstr_t cnstr1, cnstr_t cnstr2) {return 0;}\n',
    '_ITE_':    'cnstr_t _ITE_(cnstr_t cnstr1, cnstr_t cnstr2, cnstr_t cnstr3) {return 0;}\n',
    '_ITE_VAR_': 'cnstr_t _ITE_VAR_(cnstr_t cnstr1, symbolic var1, symbolic var2) {return 0;}\n'
}

# Merge all
all_api = {
    'save_current_state':       'state_t save_current_state() {return 0;}\n',
    'get_cnstr':                'cnstr_t get_cnstr(symbolic var, size_t size) {return 0;}\n',
    'store_cnstr':              'void store_cnstr(char* name, cnstr_t constraint) {return;}\n',
    'halt_all':                 'void halt_all(state_t state) {return;}\n',
    'check_implications':       'result_t check_implications(char* constraint1, char* constraint2) {return 0;}\n',
    'print_counterexamples':    'void print_counterexamples(result_t result) {return;}\n',
    'sym_var_named':            'symbolic sym_var_named(char* name, size_t size) {return 0;}\n',
    'sym_var_array':            'symbolic sym_var_array(char* name, size_t index, size_t size) {return 0;}\n',
    'mem_addr':                 'void mem_addr(char* name, void* addr, size_t length) {return;}\n',
    'maximize':                 'long maximize(symbolic sym_var){return 0;}\n',
    'sym_var':                  'symbolic sym_var(size_t size) {return 0;}\n',
    'is_symbolic':              'int is_symbolic(symbolic sym_var) {return 0;} \n',
    'assume':                   'void assume(cnstr_t cnstr) {return;}\n',
    'is_certain':               'int is_certain(cnstr_t cnstr){return 0;}\n',
    'is_sat':                   'int is_sat(cnstr_t cnstr); \n',
    '_assert':                  'void _assert(int expr){return;}\n',
    'push_pc':                  'void push_pc(){return;}\n',
    'pop_pc':                   'void pop_pc(){return;}\n',
    '_EQ_':                     'cnstr_t _EQ_(symbolic var1, symbolic var2) {return 0;}\n',
    '_NEQ_':                    'cnstr_t _NEQ_(symbolic var1, symbolic var2) {return 0;}\n',
    '_LT_':                     'cnstr_t _LT_(symbolic var1, symbolic var2) {return 0;}\n',
    '_LE_':                     'cnstr_t _LE_(symbolic var1, symbolic var2) {return 0;}\n',
    '_ULT_':                    'cnstr_t _ULT_(symbolic var1, symbolic var2) {return 0;}\n',
    '_ULE_':                    'cnstr_t _ULE_(symbolic var1, symbolic var2) {return 0;}\n',
    '_GT_':                     'cnstr_t _GT_(symbolic var1, symbolic var2) {return 0;}\n',
    '_GE_':                     'cnstr_t _GE_(symbolic var1, symbolic var2) {return 0;}\n',
    '_UGT_':                    'cnstr_t _UGT_(symbolic var1, symbolic var2) {return 0;}\n',
    '_UGE_':                    'cnstr_t _UGE_(symbolic var1, symbolic var2) {return 0;}\n',
    '_NOT_':                    'cnstr_t _NOT_(cnstr_t cnstr) {return 0;}\n',
    '_OR_':                     'cnstr_t _OR_(cnstr_t cnstr1, cnstr_t cnstr2) {return 0;}\n',
    '_AND_':                    'cnstr_t _AND_(cnstr_t cnstr1, cnstr_t cnstr2) {return 0;}\n',
    '_ITE_':                    'cnstr_t _ITE_(cnstr_t cnstr1, cnstr_t cnstr2, cnstr_t cnstr3) {return 0;}\n',
    '_ITE_VAR_':                'cnstr_t _ITE_VAR_(cnstr_t cnstr1, symbolic var1, symbolic var2) {return 0;}\n'
}
