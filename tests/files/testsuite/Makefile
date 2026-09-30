SHELL := /bin/bash

GREEN   := \033[0;32m
RED     := \033[0;31m
YELLOW  := \033[33m
MAGENTA := \033[35m
RESET   := \033[0m

FLAGS  := -Wno-int-conversion -Wno-pointer-to-int-cast

# FS=ours (default) or FS=angr, for angr's native file system
FS ?= ours

ifeq ($(FS),angr)
SUMMBV := summbv -angr-fs -run --binary
else
SUMMBV := summbv -run --binary
endif

BINS  	 := bins

# SYM_FILE=N makes the tests' file names N symbolic bytes and a '\0'
# (default 1). Its binaries go to their own directory, so builds never mix.
ifdef SYM_FILE
FLAGS += -DFNAME_BYTES=$(SYM_FILE)
BINS  := bins/sym-file-$(SYM_FILE)
endif

LIB_PATH := lib

LIB := $(LIB_PATH)/sra.c -I$(LIB_PATH)

# KLEE test suite (submodule), written against the API in lib/sra.h
KLEE_DIR := klee-testsuite/individual-tests
KLEE_INC := -Iklee-testsuite/include

# Tests are named by their path without .c: open/test_01, ...
TESTS := $(patsubst $(KLEE_DIR)/%.c,%,$(wildcard $(KLEE_DIR)/*/test_*.c))

# TEST=open/test_01 runs one test with its output shown
# SUITE=open runs one suite
ifdef TEST
TESTS := $(TEST:.c=)
QUIET :=
else
QUIET := > /dev/null 2>&1
endif

ifdef SUITE
TESTS := $(filter $(SUITE)/%,$(TESTS))
endif

.PHONY: sra compile run run-all clean

sra:
	../sra.py $(LIB_PATH)

$(BINS)/%.test: $(KLEE_DIR)/%.c klee-testsuite/include/test_helper.h
	@mkdir -p $(@D)
	$(CC) $(FLAGS) $(KLEE_INC) $< $(LIB) -o $@

compile: sra $(TESTS:%=$(BINS)/%.test)

run:
	@echo -e "$(YELLOW)== File system: $(FS) ==$(RESET)"; \
	passed=0; \
	failed=0; \
	for test in $(TESTS); do \
		echo -e -n "$(YELLOW)->$(RESET) $(MAGENTA)$$test$(RESET)  "; \
		if $(MAKE) -s $(BINS)/$$test.test && $(SUMMBV) $(BINS)/$$test.test $(QUIET); then \
			passed=$$((passed + 1)); \
			echo -e "$(GREEN)Passed!$(RESET)"; \
		else \
			failed=$$((failed + 1)); \
			echo -e "$(RED)Failed!$(RESET)"; \
		fi; \
	done; \
	echo -e "$(GREEN)Passed:$(RESET) $$passed"; \
	echo -e "$(RED)Failed:$(RESET) $$failed"; \
	[ $$failed -eq 0 ]

run-all:
	@$(MAKE) -s run FS=ours; ours=$$?; \
	$(MAKE) -s run FS=angr && [ $$ours -eq 0 ]

clean:
	$(RM) -r $(BINS)/*.test $(BINS)/*/
