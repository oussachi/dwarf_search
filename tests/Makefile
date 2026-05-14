# Makefile — build stripped and unstripped ELF binaries for both test programs
#
# Produces four binaries:
#   bin/test_c           - unstripped C binary
#   bin/test_c.stripped  - stripped C binary
#   bin/test_cpp         - unstripped C++ binary
#   bin/test_cpp.stripped- stripped C++ binary
#
# Usage:
#   make          - build everything
#   make clean    - remove bin/

CC      := gcc
CXX     := g++
# -g         : include DWARF debug info (populates .symtab with full names)
# -fno-inline: prevent inlining so small helpers don't disappear
CFLAGS  := -g -fno-inline -Wall
CXXFLAGS:= -g -fno-inline -Wall -std=c++17
STRIP   := strip

BINDIR  := bin

# ── targets ────────────────────────────────────────────────────────────────

.PHONY: all clean

all: \
    $(BINDIR)/test_c \
    $(BINDIR)/test_c.stripped \
    $(BINDIR)/test_cpp \
    $(BINDIR)/test_cpp.stripped

$(BINDIR):
	mkdir -p $(BINDIR)

# C — unstripped
$(BINDIR)/test_c: test_c.c | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $<

# C — stripped  (copy then strip so the unstripped original is preserved)
$(BINDIR)/test_c.stripped: $(BINDIR)/test_c
	cp $< $@
	$(STRIP) --strip-all $@

# C++ — unstripped
$(BINDIR)/test_cpp: test_cpp.cpp | $(BINDIR)
	$(CXX) $(CXXFLAGS) -o $@ $<

# C++ — stripped
$(BINDIR)/test_cpp.stripped: $(BINDIR)/test_cpp
	cp $< $@
	$(STRIP) --strip-all $@

clean:
	rm -rf $(BINDIR)
