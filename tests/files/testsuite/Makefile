# Runs the file-system test suite in klee-testsuite/ on one file system, and
# saves each test's output as a log. See README.md.
#
#   make run [-jN] [FS=ours|angr|klee|native] [SUITE=open | TEST=open/test_01]
#            [SYM_FILE=N | CNCR_FILE=N] [LOG=dir] [SUMMARIES=dir]

SHELL := /bin/bash

GREEN   := \033[0;32m
RED     := \033[0;31m
YELLOW  := \033[33m
MAGENTA := \033[35m
RESET   := \033[0m


# -- Options ---------------------------------------------------------------

# The file system: ours (default), angr (angr's native one), klee (KLEE, in
# Docker) or native (Linux itself, as the reference)
FS ?= ours

# Where the logs go: $(LOG)/<fs>/<kind of file names>/<test>.log. LOG= keeps none.
LOG ?= logs


# -- File names ------------------------------------------------------------

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


# -- How each file system builds and runs a test ---------------------------

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


# -- Summaries -------------------------------------------------------------

# SUMMARIES=dir links every dir/*/*.c into the tests, so that the libc
# functions the summaries are named after (read, ...) run the summaries. They
# are written for 32 bits, as the fuzzer builds them, so the tests are too.
ifdef SUMMARIES
ifneq ($(FS),ours)
$(error SUMMARIES needs FS=ours)
endif

SUMMARY_SRCS := $(wildcard $(SUMMARIES)/*/*.c)
ifeq ($(SUMMARY_SRCS),)
$(error No summaries in $(SUMMARIES)/*/*.c)
endif

FLAGS += -m32 -Wno-implicit-function-declaration
LIB   += $(SUMMARY_SRCS)
BINS  := bins/summaries/$(FNAME_KIND)
endif


# -- Tests -----------------------------------------------------------------

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


# -- Logs ------------------------------------------------------------------

# Each test's output goes to its log, which run then ends with "== PASSED" or
# "== FAILED" for report.py. With TEST=, it is shown as well.
RUN_KIND := $(FS)$(if $(SUMMARIES),-summaries)/$(FNAME_KIND)
LOG_FILE := $(LOG)/$(RUN_KIND)/$$test.log

ifdef TEST
OUTPUT := $(if $(LOG),2>&1 | tee $(LOG_FILE))
else
OUTPUT := $(if $(LOG),> $(LOG_FILE),> /dev/null) 2>&1
endif

# Each test's verdict, PASSED or FAILED, for run to count
VERDICTS := bins/.verdicts/$(RUN_KIND)


# -- Targets ---------------------------------------------------------------

.PHONY: run run-all compile sra klee-image clean clean-logs

# Runs every test, in parallel with -jN, then counts the verdicts
run:
	@echo -e "$(YELLOW)== File system: $(FS) ==$(RESET)"
	@$(RM) -r $(VERDICTS)
	@$(MAKE) --no-print-directory -k $(TESTS:%=run/%) || true
	@passed=$$(grep -lx PASSED $(VERDICTS)/*/* 2>/dev/null | wc -l); \
	failed=$$(grep -lx FAILED $(VERDICTS)/*/* 2>/dev/null | wc -l); \
	echo -e "$(GREEN)Passed:$(RESET) $$passed"; \
	echo -e "$(RED)Failed:$(RESET) $$failed"; \
	[ $$failed -eq 0 ] && [ $$passed -eq $(words $(TESTS)) ]

# One test: builds it, runs it, and saves its log and its verdict
run/%:
	@set -o pipefail; \
	test=$*; \
	mkdir -p $(VERDICTS)/$$(dirname $$test); \
	$(if $(LOG),mkdir -p $$(dirname $(LOG_FILE));) \
	if $(BUILD_TEST) && $(RUN_TEST) $(OUTPUT); then \
		verdict=PASSED; \
		line="$(GREEN)Passed!$(RESET)"; \
	else \
		verdict=FAILED; \
		line="$(RED)Failed!$(RESET)"; \
	fi; \
	echo $$verdict > $(VERDICTS)/$$test; \
	$(if $(LOG),echo "== $$verdict" >> $(LOG_FILE);) \
	echo -e "$(YELLOW)->$(RESET) $(MAGENTA)$$test$(RESET)  $$line"

# Our file system, then angr's
run-all:
	@$(MAKE) -s run FS=ours; ours=$$?; \
	$(MAKE) -s run FS=angr && [ $$ours -eq 0 ]

# Regenerates lib/ from the API, then builds every test
compile: sra $(TESTS:%=$(BINS)/%.test)

sra:
	../sra.py lib

$(BINS)/%.test: $(SUITE_DIR)/%.c klee-testsuite/include/test_helper.h $(SUMMARY_SRCS)
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
