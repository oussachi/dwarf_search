#!/usr/bin/env python3
"""
compare.py
----------
For each test program, extract functions two ways and print them side by side:

  LEFT  (unstripped) — read .symtab directly; gives us the ground truth
                       list of functions with their real names.
  RIGHT (stripped)   — run the .eh_frame inspector; gives us address ranges
                       with no names.

The comparison lets you verify that every range found by .eh_frame matches
a real symbol, and spot anything missed or spurious.

Usage:
    python compare.py [--bin-dir bin]

The script expects the four binaries produced by the Makefile:
    <bin_dir>/test_c            (unstripped)
    <bin_dir>/test_c.stripped   (stripped)
    <bin_dir>/test_cpp          (unstripped)
    <bin_dir>/test_cpp.stripped (stripped)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    from elftools.elf.elffile import ELFFile
except ImportError:
    sys.exit("pyelftools is required:  pip install pyelftools")

try:
    from dwarf_search import extract_functions as functions_from_eh_frame
except ImportError:
    sys.exit("dwarf_search.py not found — make sure it is in the same directory.")


# ── name demangling + shortening ─────────────────────────────────────────────

def demangle_batch(names: list[str]) -> list[str]:
    """
    Demangle a list of C++ mangled names in one c++filt subprocess call.
    Names that are not mangled (no leading _Z) are returned as-is.
    Falls back gracefully if c++filt is not on PATH.
    """
    if not names:
        return names
    try:
        result = subprocess.run(
            ["c++filt"],
            input="\n".join(names),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return names   # c++filt unavailable — return raw names unchanged


def shorten(name: str, max_len: int = 35) -> str:
    """
    Produce a human-readable short form of a demangled C++ symbol.

    Steps:
      1. Collapse template args to <>  and parameter lists to ()  using a
         bracket-depth loop (regex can't handle nesting).
      2. Strip a leading return-type word when safe — i.e. when the first
         space-separated token contains no ':' or '(' and the second token
         is not part of an "operator X" name.
      3. Drop common noisy namespace prefixes (std::, __gnu_cxx::, …).
      4. Hard-truncate with '…' if still over max_len.
    """
    if name == "<unknown>":
        return name

    def collapse(s: str, op: str, cl: str) -> str:
        out, depth = [], 0
        for ch in s:
            if ch == op:
                depth += 1
                if depth == 1:
                    out.append(op)
            elif ch == cl:
                depth -= 1
                if depth == 0:
                    out.append(cl)
            elif depth == 0:
                out.append(ch)
        return "".join(out)

    # Step 1 — collapse angle-brackets then parens
    name = collapse(name, "<", ">")
    name = collapse(name, "(", ")")

    # Step 2 — strip leading return-type token.
    # After collapsing, the name looks like one of:
    #   "void foo()"               → strip "void"
    #   "double mean<>()"          → strip "double"
    #   "operator bool() const"    → keep (second word is "bool", preceded by "operator")
    #   "Matrix::operator+()"      → no leading type (no space before "::")
    #   "bool() const"             → "bool" is the function name itself (operator bool)
    parts = name.split(" ", 1)
    if len(parts) == 2:
        first, rest = parts
        # Only strip when the first token looks like a plain type:
        # no ':', no '<', no '(', no '*', no '&', no '~'
        # AND the remainder does not start with a bare type word
        # (meaning rest actually contains the qualified function name)
        is_plain_type = not any(c in first for c in ":(<)*&~")
        is_operator   = rest.startswith("operator") or "::operator" in rest
        has_qualifier = "::" in rest or rest[0].isupper() or rest[0] == "_"
        if is_plain_type and not is_operator and has_qualifier:
            name = rest

    # Step 3 — drop noisy namespace prefixes
    for ns in ["std::__cxx11::", "std::__1::", "__gnu_cxx::", "std::"]:
        name = name.replace(ns, "")

    # Step 4 — hard truncate
    if len(name) > max_len:
        name = name[:max_len - 1] + "…"

    return name.strip()


# ── symbol-table extraction (unstripped) ─────────────────────────────────────

def functions_from_symtab(path: Path) -> list[dict]:
    """Read STT_FUNC symbols from .symtab — ground truth for unstripped ELFs."""
    results = []
    with path.open("rb") as f:
        elf = ELFFile(f)
        symtab = elf.get_section_by_name(".symtab")
        if symtab is None:
            return results
        for sym in symtab.iter_symbols():
            if (sym.entry["st_info"]["type"] == "STT_FUNC"
                    and sym["st_value"] != 0
                    and sym["st_size"] != 0):
                results.append({
                    "start": sym["st_value"],
                    "end":   sym["st_value"] + sym["st_size"],
                    "size":  sym["st_size"],
                    "name":  sym.name,
                })
    results.sort(key=lambda x: x["start"])

    # demangle all names in one subprocess call, then shorten for display
    raw_names     = [fn["name"] for fn in results]
    demangled     = demangle_batch(raw_names)
    for fn, dem in zip(results, demangled):
        fn["name"] = shorten(dem)

    return results


# ── side-by-side printer ──────────────────────────────────────────────────────

AW = 18   # address column  "0x0000000000001234"
SW = 8    # size column
NW = 38   # name column

def fmt_row(start: int, size: int, name: str) -> str:
    return f"0x{start:016x}  {size:>{SW}}  {name:<{NW}}"

SEP_COL  = "  │  "
SEP_LINE = "─" * (AW + SW + NW + 4)


def print_side_by_side(label: str,
                       symtab_fns: list[dict],
                       eh_fns:     list[dict]) -> None:

    total_w = len(SEP_LINE) * 2 + len(SEP_COL)
    print(f"\n{'═' * total_w}")
    print(f"  {label}")
    print(f"{'═' * total_w}")

    hdr_left  = f"{'START':<{AW}}  {'SIZE':>{SW}}  {'SYMTAB NAME':<{NW}}"
    hdr_right = f"{'START':<{AW}}  {'SIZE':>{SW}}  {'EH_FRAME (no name)':<{NW}}"
    print(f"  {hdr_left}{SEP_COL}{hdr_right}")
    print(f"  {SEP_LINE}{SEP_COL}{SEP_LINE}")

    sym_by_addr = {fn["start"]: fn for fn in symtab_fns}
    eh_by_addr  = {fn["start"]: fn for fn in eh_fns}
    all_addrs   = sorted(set(sym_by_addr) | set(eh_by_addr))

    matched = missed = extra = 0

    for addr in all_addrs:
        sym = sym_by_addr.get(addr)
        eh  = eh_by_addr.get(addr)

        left  = fmt_row(sym["start"], sym["size"], sym["name"]) if sym \
                else " " * (AW + SW + NW + 4)
        right = fmt_row(eh["start"],  eh["size"],  "<unknown>") if eh \
                else " " * (AW + SW + NW + 4)

        if sym and eh:
            tag = "✓" if sym["size"] == eh["size"] else "≈ size differs"
            matched += 1
        elif sym and not eh:
            tag = "✗ missed by eh_frame"
            missed += 1
        else:
            tag = "? extra in eh_frame"
            extra += 1

        print(f"  {left}{SEP_COL}{right}  {tag}")

    print(f"\n  symtab functions  : {len(symtab_fns)}")
    print(f"  eh_frame regions  : {len(eh_fns)}")
    print(f"  matched           : {matched}/{len(all_addrs)}")
    if missed:
        print(f"  missed by eh      : {missed}")
    if extra:
        print(f"  extra in eh       : {extra}")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare symtab vs .eh_frame function detection side-by-side"
    )
    parser.add_argument(
        "--bin-dir", default="tests/bin",
        help="Directory containing the four test binaries (default: bin)"
    )
    args = parser.parse_args()

    bd = Path(args.bin_dir)

    pairs = [
        ("C program",   bd / "test_c",   bd / "test_c.stripped"),
        ("C++ program", bd / "test_cpp", bd / "test_cpp.stripped"),
    ]

    for label, unstripped, stripped in pairs:
        for p in (unstripped, stripped):
            if not p.exists():
                sys.exit(
                    f"Binary not found: {p}\n"
                    f"Run 'make' in the directory with the Makefile first."
                )
        sym_fns = functions_from_symtab(unstripped)
        eh_fns  = functions_from_eh_frame(stripped)
        print_side_by_side(label, sym_fns, eh_fns)

    print()


if __name__ == "__main__":
    main()