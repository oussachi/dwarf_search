# DWARF_Search

Recover function boundaries from stripped ELF binaries by parsing the `.eh_frame` section — no symbol table required.

---

## How it works

When a compiler builds a C or C++ binary it emits a section called `.eh_frame` alongside the code. This section exists to support C++ exception unwinding and `backtrace()` at runtime, so **it survives `strip --strip-all`** — the dynamic linker needs it. It has nothing to do with debug info.

`.eh_frame` is a sequence of DWARF Call Frame Information (CFI) records of two types:

- **CIE** (Common Information Entry) — a shared descriptor reused by many functions; describes calling convention, return address register, and augmentation format.
- **FDE** (Frame Description Entry) — one per function; stores the function's start address (`initial_location`) and its byte length (`address_range`).

DWARF_Search walks all FDEs and emits `start → end` ranges, optionally cross-referencing the symbol table when it is present.

---

## Files

| File | Purpose |
|---|---|
| `dwarf_search.py` | Main tool — extracts functions from `.eh_frame` |
| `tests/compare.py` | Test harness — symtab vs `.eh_frame` side-by-side |
| `tests/test_c.c` | C test program with several distinct functions |
| `tests/test_cpp.cpp` | C++ test program with classes, templates, exceptions |
| `tests/Makefile` | Builds four binaries (stripped + unstripped for each) |

---

## Installation

```bash
pip install pyelftools
```

---

## Usage

### `dwarf_search.py` — inspect any ELF binary

```bash
# Basic usage — sorted by address
python dwarf_search.py ./target

# Sort by function size (largest first)
python dwarf_search.py ./target --sort size

```

**Options:**

```
positional arguments:
  binary                Path to the ELF binary

options:
  --sort {addr,size,name}
                        Sort order (default: addr)
  --json                Output as JSON instead of a table
```

**Example output (stripped binary):**

```
Binary : ./bin/test_c.stripped
Arch   : ELF64

----------------------------------------------------------------------
Start               End                 Size (bytes)  Name
----------------------------------------------------------------------
0x000000000000102c  0x0000000000001050            36  <unknown>
0x00000000000010a0  0x00000000000010c6            38  <unknown>
0x0000000000001189  0x000000000000118d             4  <unknown>
0x000000000000118d  0x00000000000011c2            53  <unknown>
0x00000000000011c2  0x00000000000011ef            45  <unknown>
0x00000000000011ef  0x0000000000001232            67  <unknown>
0x0000000000001232  0x0000000000001266            52  <unknown>
0x0000000000001266  0x00000000000012d0           106  <unknown>
0x00000000000012d0  0x0000000000001429           345  <unknown>
----------------------------------------------------------------------
  Total functions found: 9
```

**Example output (unstripped binary — names resolved from `.symtab`):**

```
Binary : ./bin/test_c
Arch   : ELF64

----------------------------------------------------------------------
Start               End                 Size (bytes)  Name
----------------------------------------------------------------------
0x00000000000010a0  0x00000000000010c6            38  _start
0x0000000000001189  0x000000000000118d             4  add
0x000000000000118d  0x00000000000011c2            53  multiply
0x00000000000011c2  0x00000000000011ef            45  fibonacci
0x00000000000011ef  0x0000000000001232            67  bubble_sort
0x0000000000001232  0x0000000000001266            52  reverse_string
0x0000000000001266  0x00000000000012d0           106  print_array
0x00000000000012d0  0x0000000000001429           345  main
----------------------------------------------------------------------
  Total functions found: 8
```

---

## Test suite

Build the four test binaries, then run the comparison:

```bash
cd tests
make
cd ..
python compare.py
```

`compare.py` reads the symbol table of the unstripped binary (ground truth) and the `.eh_frame` of the stripped binary, then prints them side by side with match annotations:

```
  ✓               address and size match exactly
  ≈ size differs  address matched, sizes differ (FDE fragment / epilogue)
  ✗ missed by eh  symbol exists but no FDE found (asm without .cfi_* directives)
  ? extra in eh   FDE exists but no STT_FUNC symbol (PLT stubs, runtime glue)
```

---

## Limitations

- **Functions compiled with `-fno-asynchronous-unwind-tables`** emit no FDEs and will not appear. This is uncommon in practice but typical in embedded or kernel code.
- **Hand-written assembly** without `.cfi_startproc` / `.cfi_endproc` directives produces no FDE.
- **Tail-call merging and identical-code folding** (ICF) can cause two logical functions to share one FDE, making them appear as a single region.
- Names are only resolved when `.symtab` or `.dynsym` is present. A fully stripped binary yields `<unknown>` for all entries — the address ranges are still accurate.

---