import sys

# Add src to path
sys.path.append(".")

from src.bindings.abc_wrapper import AbcInterface  # ty:ignore[unresolved-import]


def convert(verilog_path: str, aiger_path: str):
    abc = AbcInterface()
    print(f"Reading {verilog_path}...")
    res = abc.run_command(f"read_verilog {verilog_path}")
    if res != 0:
        print("Error reading verilog")
        sys.exit(1)

    print("Strashing...")
    res = abc.run_command("strash")
    if res != 0:
        print("Error strashing")
        sys.exit(1)

    print(f"Writing {aiger_path}...")
    res = abc.run_command(f"write_aiger {aiger_path}")
    if res != 0:
        print("Error writing aiger")
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert.py input.v output.aig")
        sys.exit(1)

    convert(sys.argv[1], sys.argv[2])
