SHELL:=/bin/bash

GREEN=\033[0;32m
RED=\033[0;31m
RESET=\033[0m

TEST = $(shell basename $(CURDIR))_validation.c
EXEC = $(shell basename $(CURDIR))_validation.test
SUMM = $(shell basename $(CURDIR)).c
RESULT = $(EXEC)_result.json

EXPECTED_TEST = expected_test.c
EXPECTED_RSLT = expected_result.json

CONFIG = config.txt

.PHONY: gen run test clean

gen:
	summbv -config $(CONFIG) -o $(TEST) --lib $(SUMM)

run:
	summbv -config $(CONFIG) -o $(TEST) --lib $(SUMM) -run
	
test:
	summbv -config $(CONFIG) -o $(TEST) --lib $(SUMM)
	
	@diff -Bb $(TEST) $(EXPECTED_TEST);\
	if [ $$? -eq 0 ]; \
	then \
		echo -e "$(GREEN)\nTest Passed!$(RESET)"; \
	else \
		echo -e "$(RED)\nTest Failed!$(RESET)"; \
	fi

test-run:

	summbv -config $(CONFIG) -o $(TEST) --lib $(SUMM) -run > /dev/null 2>&1
	@diff -Bb  <(sed '3q;d' $(EXPECTED_RSLT)) <(sed '3q;d' $(RESULT));\
	if [ $$? -eq 0 ]; \
	then \
		echo -e "$(GREEN)\nTest Passed!$(RESET)"; \
	else \
		echo -e "$(RED)\nTest Failed!$(RESET)"; \
	fi

clean:
	$(RM) *.o *.test $(TEST) $(EXEC) $(RESULT)