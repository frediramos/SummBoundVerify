SHELL := /bin/bash

GREEN   := \033[0;32m
RED     := \033[0;31m
YELLOW  := \033[33m
MAGENTA := \033[35m
RESET   := \033[0m

FLAGS  := -Wno-int-conversion
SUMMBV := summbv -run --binary

BINS  := bins
TESTS := $(patsubst %.c,%.test,$(wildcard *.c))

.PHONY: compile run clean

%.test: %.c
	$(CC) $(FLAGS) $< -o $(BINS)/$@

compile: $(TESTS)

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
		echo -e "$(YELLOW)->$(RESET) $(MAGENTA)$$test$(RESET)"; \
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
		echo; \
	done; \
	\
	echo -e "$(GREEN)Passed:$(RESET) $$passed"; \
	echo -e "$(RED)Failed:$(RESET) $$failed"; \
	exit $$status

clean:
	$(RM) $(BINS)/*.test