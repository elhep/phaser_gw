VERILOG_SOURCES = $(XILINX_VIVADO)/data/verilog/src/glbl.v $(PWD)/../build/phaser.v
TOPLEVEL=phaser
TOPLEVEL_LANG=verilog
MODULE=tb_phaser
SIM=questa
WAVES=1
SHELL := /bin/bash
GUI=0

SIM_ARGS=-voptargs=\"-L unisims_ver -L unimacro_ver -L secureip\" work.glbl

#COMPILE_ARGS=-y$(XILINX_VIVADO)/data/verilog/src/unisims -s glbl

include $(shell cocotb-config --makefiles)/Makefile.inc
include $(shell cocotb-config --makefiles)/Makefile.sim
