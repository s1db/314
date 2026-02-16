# Checkers

This directory contains verification tools (checkers) for validating QBF solver outputs. We do not provide the solvers for checking the proofs, feel free to use your own. For our experiments we used Cadical for checking the proofs.

## Quick Start

### Setup

Run the setup script to build all checkers:

```bash
./get_checkers.sh
```

This will download, patch, build, and install:
- **certcheck**: Certificate checker for QBF instances.
- **caqe_certcheck**: CAQE's certificate checker.
- **Manthan/checkSkolem**: Skolem function verification tool.

### Usage

#### CertCheck

Verifies AIGER certificates against QDIMACS formulas:

```bash
./certcheck <qdimacs_file> <certificate_aag_file> | cadical -q
```
Expected output: `s UNSATISFIABLE`

#### CAQE CertCheck

Similar to certcheck but for CAQE-generated certificates:

```bash
./caqe_certcheck <qdimacs_file> <certificate_aag_file> | aigtocnf | cadical -q
```

Expected output: `s UNSATISFIABLE`

#### checkSkolem

Verifies Verilog Skolem functions:

```bash
./checkSkolem --qdimacs <qdimacs_file> --skolem <verilog_file>
```

Expected output: `c [main] [X.XXs] skolem check UNSAT (no counterexample)`

## Patches

The build process applies minimal patches to fix compatibility and performance issues:

### certcheck_fix.patch

**Changes:**
1. **simpleaig.c**: Added `#include <unistd.h>` for macOS compatibility
2. **certcheck.c**: Added visited array logic to prevent exponential traversal

**Why:**
- **unistd.h**: Required for macOS systems where `sys/unistd.h` doesn't provide all necessary declarations.
- **Visited array**: The patch adds a visited tracking mechanism to ensure each node is processed only once, preventing infinite loops.

**Details:**
```c
// Added declaration
char *visited;

// Initialization before traversal
visited = (char *) malloc ((aig->max_var + 1) * sizeof (char));
memset (visited, 0, (aig->max_var + 1) * sizeof (char));

// Check before processing
if (visited[abs(lhs)]) continue;
visited[abs(lhs)] = 1;

// Cleanup
free(visited);
```

### checkSkolem_fix.patch

**Changes:**
- **checkSkolem.py**: Fixed path resolution in `_static_bin_path()` function

**Why:**
Original code used relative path `"./dependencies/static_bin"` which failed when script was run from different directories. The patch changes it to use `REPO_ROOT` for absolute path resolution.

**Details:**
```diff
- preferred = os.path.join("./dependencies/static_bin", bin_name)
+ preferred = os.path.join(REPO_ROOT, "dependencies", "static_bin", bin_name)
```

## Build Details

### ABC Helpers

The build process compiles ABC helper binaries from source:
- `file_generation_cex`: Generates counterexamples
- `file_generation_cnf`: Converts to CNF format
- `file_write_verilog`: Writes Verilog output

These are built from the ABC repository and placed in `manthan/dependencies/static_bin/`.

### Directory Structure

After building:
```
checkers/
├── certcheck              -> certcheck_tool/certcheck (symlink)
├── certcheck_tool/        (CertCheck installation)
├── caqe                   -> caqe_tool/caqe (symlink)
├── caqe_certcheck         -> caqe_tool/certcheck (symlink)
├── caqe_tool/             (CAQE installation)
├── checkSkolem            (wrapper script)
├── manthan/               (Manthan installation)
│   ├── checkSkolem.py
│   ├── dependencies/
│   │   ├── abc/
│   │   └── static_bin/    (ABC helpers)
│   └── venv/              (Python virtual environment)
├── certcheck_fix.patch
├── checkSkolem_fix.patch
└── get_checkers.sh
```

## Troubleshooting

### certcheck fails with "undeclared identifier"
- Ensure patches are applied correctly
- Rebuild: `rm -rf certcheck_tool && ./get_checkers.sh`

### checkSkolem can't find ABC helpers
- Check `manthan/dependencies/static_bin/` contains the binaries
- Rebuild Manthan section: `rm -rf manthan && ./get_checkers.sh`

### Python dependency errors
- Activate the virtual environment: `source manthan/venv/bin/activate`
- Install requirements: `pip install -r manthan/requirements.txt`
