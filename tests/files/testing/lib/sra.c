#include "sra.h"

long __concretize(symbolic var) { return 0; }
void __assert(cnstr_t cnstr) { }
void __report_error(const char *filename, unsigned int line, const char *message) { }
long __maximize(symbolic var) { return 0; }
long __minimize(symbolic var) { return 0; }
symbolic __sym_var(size_t size) { return 0; }
symbolic __sym_var_named(char *name, size_t size) { return 0; }
symbolic __sym_var_array(char *name, size_t index, size_t size) { return 0; }
int __is_symbolic(symbolic var) { return 0; }
int __is_sat(cnstr_t cnstr) { return 0; }
int __is_certain(cnstr_t cnstr) { return 0; }
void __assume(cnstr_t cnstr) { }
void __push_pc(void) { }
void __pop_pc(void) { }
cnstr_t _NOT_(cnstr_t cnstr) { return 0; }
cnstr_t _OR_(cnstr_t cnstr1, cnstr_t cnstr2) { return 0; }
cnstr_t _AND_(cnstr_t cnstr1, cnstr_t cnstr2) { return 0; }
cnstr_t _LT_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _LE_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _GT_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _GE_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _EQ_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _NEQ_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _ULT_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _ULE_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _UGT_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _UGE_(symbolic var1, symbolic var2) { return 0; }
cnstr_t _ITE_(cnstr_t cond, cnstr_t cnstr1, cnstr_t cnstr2) { return 0; }
cnstr_t _ITE_VAR_(cnstr_t cond, symbolic var1, symbolic var2) { return 0; }
list_t __lst_mk(void) { return 0; }
list_t __lst_cons(symbolic value, list_t lst) { return 0; }
cnstr_t __lst_empty(list_t lst) { return 0; }
list_t __lst_tl(list_t lst) { return 0; }
symbolic __lst_hd(list_t lst) { return 0; }
size_t __lst_len(list_t lst) { return 0; }
list_t __lst_nbytes(char c, size_t n) { return 0; }
list_t __lst_zeros(size_t n) { return 0; }
void __cond_write(void *ptr, symbolic c, cnstr_t pc) { }
void *__mem_alloc(size_t nbytes) { return 0; }
void __mem_free(void *ptr) { }
size_t __n_allocd(void *ptr) { return 0; }
size_t __allocd(void *ptr) { return 0; }
int __file_create(const char *name) { return 0; }
int __file_open(const char *name, const char *flags) { return 0; }
int __file_exists(const char *name) { return 0; }
int __file_delete(const char *name) { return 0; }
int __file_close(int fd) { return 0; }
ssize_t __file_read(int fd, void *buffer, size_t count) { return 0; }
ssize_t __file_write(int fd, const void *buffer, size_t count) { return 0; }
ssize_t __file_size(int fd) { return 0; }
ssize_t __file_offset(int fd) { return 0; }
ssize_t __file_set_size(int fd, size_t size) { return 0; }
ssize_t __file_set_offset(int fd, size_t offset) { return 0; }
int __file_set_mode(int fd, mode_t mode) { return 0; }
int __file_mode(int fd, mode_t *mode) { return 0; }
int __file_flags(int fd) { return 0; }
int __file_dup(int oldfd) { return 0; }
int __file_dup2(int oldfd, int newfd) { return 0; }
FILE *__FILE_from_fd(int fd) { return 0; }
int __fd_from_FILE(FILE *fp) { return 0; }
