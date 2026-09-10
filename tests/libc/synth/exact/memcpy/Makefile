SHELL := /bin/bash

GREEN = \033[0;32m
RED   = \033[0;31m
RESET = \033[0m

TEST   = $(notdir $(CURDIR))_validation.c
EXEC   = $(notdir $(CURDIR))_validation.test
SUMM   = $(notdir $(CURDIR)).c
RESULT = $(EXEC)_result.json

EXPECTED_TEST = expected_test.c
EXPECTED_RSLT = expected_result.json

CONFIG = config.txt
LIB    = lib.c

SUMMBV = summbv -config $(CONFIG) -o $(TEST) --lib $(SUMM) -memory

.PHONY: gen run test test-run clean

gen:
	$(SUMMBV)

run:
	$(SUMMBV) -run

test: clean
	$(SUMMBV)

	@diff -Bb $(TEST) $(EXPECTED_TEST); \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo -e "$(GREEN)\nTest Passed!$(RESET)"; \
	else \
		echo -e "$(RED)\nTest Failed!$(RESET)"; \
	fi; \
	exit $$status

test-run: clean
	@$(SUMMBV) -run > /dev/null 2>&1

	@diff -Bb <(sed -n '3,4p' $(EXPECTED_RSLT)) <(sed -n '3,4p' $(RESULT)); \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo -e "$(GREEN)\nTest Passed!$(RESET)"; \
	else \
		echo -e "$(RED)\nTest Failed!$(RESET)"; \
	fi; \
	exit $$status

clean:
	$(RM) *.o *.test $(TEST) $(EXEC) $(RESULT)
	$(RM) -r *.aflwork *.fuzz *-fuzz.c *fuzz_result.json