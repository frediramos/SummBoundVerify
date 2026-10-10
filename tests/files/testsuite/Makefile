# Runs the file-system test suite in klee-testsuite/ on one file system, and
# saves each test's output as a log. See README.md.
#
#   make run [FS=ours|angr|klee|native] [SUITE=open | TEST=open/test_01]
#            [SYM_FILE=N | CNCR_FILE=N] [LOG=dir]

SHELL := /bin/bash

GREEN   := \033[0;32m
RED     := \033[0;31m
YELLOW  := \033[33m
MAGENTA := \033[35m
RESET   := \033[0m


# ── Options ───────────────────────────────────────────────────────────────

# The file system: ours (default), angr (angr's native one), klee (KLEE, in
# Docker) or native (Linux itself, as the reference)
FS ?= ours

# Where the logs go: $(LOG)/<fs>/<kind of file names>/<test>.log. LOG= keeps none.
LOG ?= logs


# ── File names ────────────────────────────────────────────────────────────

# The tests' file names: N symbolic bytes and a '\0' (SYM_FILE=N, default 1),
# or N concrete characters, "AA...", "BB...", ... (CNCR_FILE=N). Native runs
# have no symbolic values, so their names are always concrete.
ifneq ($(and $(SYM_FILE),$(CNCR_FILE)),)
$(error SYM_FILE and CNCR_FILE cannot be used together)
endif
ifeq ($(FS)-$(if $(SYM_FILE),sym),native-sym)
$(error FS=native has no symbolic file names: use CNCR_FILE)
endif
ifeq ($(FS),klee)
ifneq ($(SYM_FILE)$(CNCR_FILE),)
$(error FS=klee takes neither SYM_FILE nor CNCR_FILE: the suite's KLEE runner builds the tests)
endif
endif

ifneq ($(CNCR_FILE),)
FNAME_KIND := cncr-fname-$(CNCR_FILE)
else ifeq ($(FS),native)
FNAME_KIND := cncr-fname-1
else
FNAME_KIND := sym-fname-$(or $(SYM_FILE),1)
endif


# ── How each file system builds and runs a test ───────────────────────────

FLAGS := -Wno-int-conversion -Wno-pointer-to-int-cast \
         -DFNAME_BYTES=$(lastword $(subst -, ,$(FNAME_KIND)))
ifneq ($(filter cncr-%,$(FNAME_KIND)),)
FLAGS += -DCONCRETE_FNAME
endif

# summbv (angr & ours) runs tests built against the API stubs in lib/ hooks
LIB  := lib/sra.c -Ilib
BINS := bins/$(FNAME_KIND)

# The image FS=klee runs in, built by klee-image
KLEE_IMAGE := klee-testsuite-fork


# Our symbolic FS
ifeq ($(FS),ours)
BUILD_TEST = $(MAKE) -s $(BINS)/$$test.test
RUN_TEST   = summbv -run --binary $(BINS)/$$test.test

# angr's FS 
else ifeq ($(FS),angr)
BUILD_TEST = $(MAKE) -s $(BINS)/$$test.test
RUN_TEST   = summbv -angr-fs -run --binary $(BINS)/$$test.test

else ifeq ($(FS),native)
# Built against the API done with real Linux calls, and run directly
FLAGS      += -DNATIVE
LIB        := native/sra_native.c -Ilib
BINS       := bins/native/$(FNAME_KIND)
BUILD_TEST = $(MAKE) -s $(BINS)/$$test.test
RUN_TEST   = native/run.sh $(BINS)/$$test.test

else ifeq ($(FS),klee)
# Built and run by the suite's own KLEE runner, in the image klee-image builds
BUILD_TEST = true
RUN_TEST   = KLEE_IMAGE=$(KLEE_IMAGE) klee/run.sh $$test

else
$(error Unknown FS=$(FS): use ours, angr, klee or native)
endif


# ── Tests ─────────────────────────────────────────────────────────────────

SUITE_DIR := klee-testsuite/individual-tests

# Tests are named by their path without .c: open/test_01, ...
TESTS := $(patsubst $(SUITE_DIR)/%.c,%,$(wildcard $(SUITE_DIR)/*/test_*.c))

# SUITE=open runs one suite; TEST=open/test_01 one test, with its output shown
ifdef SUITE
TESTS := $(filter $(SUITE)/%,$(TESTS))
endif
ifdef TEST
TESTS := $(TEST:.c=)
endif


# ── Logs ──────────────────────────────────────────────────────────────────

# Each test's output goes to its log, which run then ends with "== PASSED" or
# "== FAILED" for report.py. With TEST=, it is shown as well.
LOG_FILE := $(LOG)/$(FS)/$(FNAME_KIND)/$$test.log

ifdef TEST
OUTPUT := $(if $(LOG),2>&1 | tee $(LOG_FILE))
else
OUTPUT := $(if $(LOG),> $(LOG_FILE),> /dev/null) 2>&1
endif


# ── Targets ───────────────────────────────────────────────────────────────

.PHONY: run run-all compile sra klee-image clean clean-logs

run:
	@set -o pipefail; \
	echo -e "$(YELLOW)== File system: $(FS) ==$(RESET)"; \
	passed=0; \
	failed=0; \
	for test in $(TESTS); do \
		echo -e -n "$(YELLOW)->$(RESET) $(MAGENTA)$$test$(RESET)  "; \
		$(if $(LOG),mkdir -p $$(dirname $(LOG_FILE));) \
		if $(BUILD_TEST) && $(RUN_TEST) $(OUTPUT); then \
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

# Our file system, then angr's
run-all:
	@$(MAKE) -s run FS=ours; ours=$$?; \
	$(MAKE) -s run FS=angr && [ $$ours -eq 0 ]

# Regenerates lib/ from the API, then builds every test
compile: sra $(TESTS:%=$(BINS)/%.test)

sra:
	../sra.py lib

$(BINS)/%.test: $(SUITE_DIR)/%.c klee-testsuite/include/test_helper.h
	@mkdir -p $(@D)
	$(CC) $(FLAGS) -Iklee-testsuite/include $< $(LIB) -o $@

# The image FS=klee runs in: KLEE built with the fork in klee-fork/
klee-image:
	docker build -t $(KLEE_IMAGE) --build-context fork=klee-fork klee-testsuite

# Removes every build (bins/ keeps its README)
clean:
	$(RM) -r bins/*/

clean-logs:
	$(RM) -r $(LOG)/*/
