SHELL := /bin/bash

GREEN = \033[0;32m
RED   = \033[0;31m
RESET = \033[0m

NAME     = $(notdir $(CURDIR))_validation
SUMMARY  = $(NAME)-summary.c
CONCRETE = $(NAME)-concrete.c
CHECK    = $(NAME)-concrete_check.json

EXPECTED_SUMMARY  = expected_summary_test.c
EXPECTED_CONCRETE = expected_concrete_test.c
EXPECTED_RSLT     = expected_result.json

CONFIG = config.yaml
EXECS ?= 2000

SUMMBV = summbv -config $(CONFIG) -o $(NAME).c --engine fuzz


.PHONY: gen run test test-run clean

gen:
	$(SUMMBV)

run:
	$(SUMMBV) -run --execs $(EXECS)

test: clean
	$(SUMMBV)

	@diff -Bb $(SUMMARY) $(EXPECTED_SUMMARY) && \
	diff -Bb $(CONCRETE) $(EXPECTED_CONCRETE); \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo -e "$(GREEN)\nTest Passed!$(RESET)"; \
	else \
		echo -e "$(RED)\nTest Failed!$(RESET)"; \
	fi; \
	exit $$status

test-run: clean
	@$(SUMMBV) -run --execs $(EXECS) > /dev/null 2>&1

	@python3 ../check_expected.py $(CHECK) $(EXPECTED_RSLT); \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo -e "$(GREEN)\nTest Passed!$(RESET)"; \
	else \
		echo -e "$(RED)\nTest Failed!$(RESET)"; \
	fi; \
	exit $$status

clean:
	$(RM) $(NAME)*
