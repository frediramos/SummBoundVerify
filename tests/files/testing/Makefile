SHELL := /bin/bash

GREEN = \033[0;32m
RED   = \033[0;31m
YELLOW  := \033[33m
MAGENTA := \033[35m
RESET = \033[0m

FLAGS  = -Wno-int-conversion
SUMMBV = summbv -run --binary

TESTS = $(patsubst %.c,%.test,$(wildcard *.c))

.PHONY: compile run clean

%.test: %.c
	$(CC) $(FLAGS) $< -o $@

compile: $(TESTS)

run: compile
	@status=0; \
	tests="$(TESTS)"; \
	if [ -n "$(TEST)" ]; then \
		tests="$(TEST:.c=).test"; \
	fi; \
	for test in $$tests; do \
		echo -e "$(YELLOW)->$(RESET) $(MAGENTA)$$test$(RESET)"; \
		$(SUMMBV) $$test; \
		result=$$?; \
		if [ $$result -eq 0 ]; then \
			echo -e "$(GREEN)Passed!$(RESET)"; \
		else \
			echo -e "$(RED)Failed!$(RESET)"; \
			status=1; \
		fi; \
		echo; \
	done; \
	exit $$status

clean:
	$(RM) *.o *.test