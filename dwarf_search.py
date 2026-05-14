#!/usr/bin/env python3
"""
---------------------
Extract code regions (functions) from an ELF binary by parsing the
.eh_frame section.

The .eh_frame section contains a series of Call Frame Information (CFI)
records defined by the DWARF standard:
  - CIE  (Common Information Entry)  - shared prologue/epilogue description
  - FDE  (Frame Description Entry)   - one per function, carries the PC range

Each FDE records:
  initial_location  - start address of the function
  address_range     - byte length of the function

We use pyelftools to locate and walk those records so we don't have to
hand-roll the LEB128/augmentation parsing ourselves.

Usage:
    python eh_frame_functions.py <elf_binary> [--json] [--sort {addr,size,name}]

Requirements:
    pip install pyelftools
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from elftools.elf.elffile import ELFFile
    from elftools.dwarf.callframe import CIE, FDE
except ImportError:
    sys.exit(
        "pyelftools is required.\n"
        "Install it with:  pip install pyelftools"
    )


# ---------------------------------------------------------------------------
# Symbol table helper
# ---------------------------------------------------------------------------

def build_symbol_map(elf: ELFFile) -> dict[int, str]:
    """Return a dict mapping address -> symbol name from .symtab / .dynsym."""
    sym_map: dict[int, str] = {}
    for section_name in (".symtab", ".dynsym"):
        section = elf.get_section_by_name(section_name)
        if section is None:
            continue
        for sym in section.iter_symbols():
            if sym.entry["st_info"]["type"] in ("STT_FUNC", "STT_NOTYPE"):
                addr = sym["st_value"]
                name = sym.name
                if addr and name:
                    sym_map.setdefault(addr, name)
    return sym_map


# ---------------------------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------------------------

def extract_functions(path: str) -> list[dict]:
    """
    Parse .eh_frame and return a list of dicts, one per FDE:
        {
            "start":  <int>  - start virtual address,
            "end":    <int>  - exclusive end address,
            "size":   <int>  - byte length,
            "name":   <str>  - symbol name or "<unknown>",
        }
    """
    p = Path(path)
    if not p.exists():
        sys.exit(f"File not found: {path}")

    results: list[dict] = []

    with p.open("rb") as f:
        elf = ELFFile(f)

        # Sanity check
        eh_frame_section = elf.get_section_by_name(".eh_frame")
        if eh_frame_section is None:
            sys.exit("No .eh_frame section found in this binary.")

        # Build symbol map for name resolution
        sym_map = build_symbol_map(elf)

        # get_dwarf_info() is required to instantiate the CFI parser,
        # but we explicitly point it at the .eh_frame section so it never
        # tries to fall back to .debug_frame (which may not exist).
        dwarf = elf.get_dwarf_info(relocate_dwarf_sections=True)

        # Walk every CFI entry in .eh_frame
        seen: set[tuple[int, int]] = set()   # deduplicate
        for entry in dwarf.EH_CFI_entries():
            if isinstance(entry, FDE):
                start = entry["initial_location"]
                size  = entry["address_range"]
                end   = start + size

                key = (start, end)
                if key in seen or size == 0:
                    continue
                seen.add(key)

                name = sym_map.get(start, "<unknown>")
                results.append(
                    {"start": start, "end": end, "size": size, "name": name}
                )

    return results


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def print_table(functions: list[dict], arch_bits: int = 64) -> None:
    addr_w = 18 if arch_bits == 64 else 10   # "0x" + 16 hex digits
    sep = "-" * (addr_w * 2 + 14 + 40)
    header = (
        f"{'Start':<{addr_w}}  {'End':<{addr_w}}  "
        f"{'Size (bytes)':>12}  {'Name'}"
    )
    print(sep)
    print(header)
    print(sep)
    for fn in functions:
        start_s = f"0x{fn['start']:0{addr_w - 2}x}"
        end_s   = f"0x{fn['end']:0{addr_w - 2}x}"
        print(
            f"{start_s:<{addr_w}}  {end_s:<{addr_w}}  "
            f"{fn['size']:>12}  {fn['name']}"
        )
    print(sep)
    print(f"  Total functions found: {len(functions)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract code regions from an ELF binary via .eh_frame"
    )
    parser.add_argument("binary", help="Path to the ELF binary")
    parser.add_argument(
        "--json", action="store_true", dest="as_json",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--sort", choices=["addr", "size", "name"], default="addr",
        help="Sort results by address (default), size, or name"
    )
    args = parser.parse_args()

    functions = extract_functions(args.binary)

    # Sort
    key_map = {
        "addr": lambda fn: fn["start"],
        "size": lambda fn: fn["size"],
        "name": lambda fn: fn["name"],
    }
    functions.sort(key=key_map[args.sort])

    if args.as_json:
        # Make addresses JSON-friendly hex strings
        output = [
            {
                "start": hex(fn["start"]),
                "end":   hex(fn["end"]),
                "size":  fn["size"],
                "name":  fn["name"],
            }
            for fn in functions
        ]
        print(json.dumps(output, indent=2))
    else:
        # Detect arch word size for pretty-printing
        with open(args.binary, "rb") as f:
            elf = ELFFile(f)
            bits = elf.elfclass          # 32 or 64
        print(f"\nBinary : {args.binary}")
        print(f"Arch   : ELF{bits}\n")
        print_table(functions, arch_bits=bits)


if __name__ == "__main__":
    main()