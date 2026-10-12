# SPDX-License-Identifier: GPL-3.0-or-later
SRC_DIR := ../Source/DIY_SPOT_WELDER_V1
CXXFLAGS ?= -std=c++14 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -I$(SRC_DIR) -I.
BUILD := build
all: run
$(BUILD)/tests: test_main.cpp sim_plant.h $(SRC_DIR)/weld_core.cpp $(SRC_DIR)/pulse_sequencer.cpp $(SRC_DIR)/*.h
	mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) test_main.cpp $(SRC_DIR)/weld_core.cpp $(SRC_DIR)/pulse_sequencer.cpp -o $@
run: $(BUILD)/tests
	./$(BUILD)/tests
clean:
	rm -rf $(BUILD)
.PHONY: all run clean
