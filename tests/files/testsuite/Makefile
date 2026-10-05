SHELL := /bin/bash

GREEN   := \033[0;32m
RED     := \033[0;31m
YELLOW  := \033[33m
MAGENTA := \033[35m
RESET   := \033[0m

FLAGS  := -Wno-int-conversion -Wno-pointer-to-int-cast

# FS=ours (default), FS=angr for angr's native file system, or FS=native to
# run the tests natively on Linux, as the reference (see native/sra_native.c)
FS ?= ours

ifeq ($(FS),angr)
SUMMBV := summbv -angr-fs -run --binary
else ifeq ($(FS),native)
SUMMBV := native/run.sh
else
SUMMBV := summbv -run --binary
endif

BINS  	 := bins

# SYM_FILE=N makes the tests' file names N symbolic bytes and a '\0'
# (default 1). Its binaries go to their own directory, so builds never mix.
ifdef SYM_FILE
FLAGS += -DFNAME_BYTES=$(SYM_FILE)
BINS  := bins/sym-fname-$(SYM_FILE)
endif

# CNCR_FILE=N makes them N concrete characters and a '\0' instead: a test's
# first name is "AA...", its second "BB...", and so on.
ifdef CNCR_FILE
ifdef SYM_FILE
$(error SYM_FILE and CNCR_FILE cannot be used together)
endif
FLAGS += -DFNAME_BYTES=$(CNCR_FILE) -DCONCRETE_FNAME
BINS  := bins/cncr-fname-$(CNCR_FILE)
endif

LIB_PATH := lib

LIB := $(LIB_PATH)/sra.c -I$(LIB_PATH)

# Native runs have no symbolic values: their file names are concrete
# (CNCR_FILE=N sets their length), and they link the native API
ifeq ($(FS),native)
ifdef SYM_FILE
$(error FS=native has no symbolic file names: use CNCR_FILE)
endif
FLAGS += -DNATIVE
BINS  := bins/native/cncr-fname-$(or $(CNCR_FILE),1)
LIB   := native/sra_native.c -I$(LIB_PATH)
endif

# The kind of file names a run uses, which keeps its logs apart
ifeq ($(FS),native)
FNAME_KIND := cncr-fname-$(or $(CNCR_FILE),1)
else
FNAME_KIND := $(if $(CNCR_FILE),cncr-fname-$(CNCR_FILE),sym-fname-$(or $(SYM_FILE),1))
endif

# KLEE test suite (submodule), written against the API in lib/sra.h
KLEE_DIR := klee-testsuite/individual-tests
KLEE_INC := -Iklee-testsuite/include

# Tests are named by their path without .c: open/test_01, ...
TESTS := $(patsubst $(KLEE_DIR)/%.c,%,$(wildcard $(KLEE_DIR)/*/test_*.c))

# TEST=open/test_01 runs one test with its output shown
# SUITE=open runs one suite

# Each test's output is saved to $(LOG_DIR)/<test>.log, ending in "== PASSED"
# or "== FAILED"; ./report.py explains them. LOG=dir saves elsewhere, LOG=
# saves nothing. Runs are kept apart by file system and kind of file names:
# logs/<fs>/sym-fname-<N>/ or logs/<fs>/cncr-fname-<N>/.
LOG ?= logs
LOG_DIR := $(LOG)/$(FS)/$(FNAME_KIND)
LOG_FILE := $(LOG_DIR)/$$test.log

ifdef TEST
TESTS  := $(TEST:.c=)
OUTPUT := $(if $(LOG),2>&1 | tee $(LOG_FILE))
else
OUTPUT := $(if $(LOG),> $(LOG_FILE),> /dev/null) 2>&1
endif

ifdef SUITE
TESTS := $(filter $(SUITE)/%,$(TESTS))
endif

.PHONY: sra compile run run-all clean clean-logs

sra:
	../sra.py $(LIB_PATH)

$(BINS)/%.test: $(KLEE_DIR)/%.c klee-testsuite/include/test_helper.h
	@mkdir -p $(@D)
	$(CC) $(FLAGS) $(KLEE_INC) $< $(LIB) -o $@

compile: sra $(TESTS:%=$(BINS)/%.test)

run:
	@set -o pipefail; \
	echo -e "$(YELLOW)== File system: $(FS) ==$(RESET)"; \
	passed=0; \
	failed=0; \
	for test in $(TESTS); do \
		echo -e -n "$(YELLOW)->$(RESET) $(MAGENTA)$$test$(RESET)  "; \
		$(if $(LOG),mkdir -p $$(dirname $(LOG_FILE));) \
		if $(MAKE) -s $(BINS)/$$test.test && $(SUMMBV) $(BINS)/$$test.test $(OUTPUT); then \
			passed=$$((passed + 1)); \
			echo -e "$(GREEN)Passed!$(RESET)"; \
			$(if $(LOG),echo "== PASSED" >> $(LOG_FILE);) \
		else \
			failed=$$((failed + 1)); \
			echo -e "$(RED)Failed!$(RESET)"; \
			$(if $(LOG),echo "== FAILED" >> $(LOG_FILE);) \
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

clean-logs:
	$(RM) -r $(LOG)/**/