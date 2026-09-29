SHELL := /bin/bash

GREEN   := \033[0;32m
RED     := \033[0;31m
YELLOW  := \033[33m
MAGENTA := \033[35m
RESET   := \033[0m

FLAGS  := -Wno-int-conversion
SUMMBV := angr -angr-fs -run --binary

BINS  	 := bins
LIB_PATH := lib

TESTS 	 := $(patsubst %.c,%.test,$(wildcard *.c))

LIB := $(LIB_PATH)/sra.c -I$(LIB_PATH)

.PHONY: sra compile run clean

sra:
	../sra.py $(LIB_PATH)

%.test: %.c
	$(CC) $(FLAGS) $< $(LIB) -o $(BINS)/$@

compile: sra $(TESTS)

run: 
	@status=0; \
	passed=0; \
	failed=0; \
	tests="$(TESTS)"; \
	single=0; \
	\
	if [ -n "$(TEST)" ]; then \
		tests="$(TEST:.c=).test"; \
		single=1; \
	fi; \
	\
	for test in $$tests; do \
		$(MAKE) -s $$test; \
		echo -e -n "$(YELLOW)->$(RESET) $(MAGENTA)$$test$(RESET)  "; \
		\
		if [ $$single -eq 1 ]; then \
			$(SUMMBV) $(BINS)/$$test; \
		else \
			$(SUMMBV) $(BINS)/$$test > /dev/null 2>&1; \
		fi; \
		\
		result=$$?; \
		\
		if [ $$result -eq 0 ]; then \
			passed=$$((passed + 1)); \
			echo -e "$(GREEN)Passed!$(RESET)"; \
		else \
			failed=$$((failed + 1)); \
			status=1; \
			echo -e "$(RED)Failed!$(RESET)"; \
		fi; \
	done; \
	\
	echo -e "$(GREEN)Passed:$(RESET) $$passed"; \
	echo -e "$(RED)Failed:$(RESET) $$failed"; \
	exit $$status

clean:
	$(RM) $(BINS)/*.test