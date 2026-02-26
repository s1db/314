#!/bin/bash
set -e

# Directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

# Temporary directory for download/extraction
TEMP_DIR="temp_download_checkers"
# Clean up previous temp dir to start fresh
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Determine core count for parallel build
if [[ "$OSTYPE" == "darwin"* ]]; then
    CORES=$(sysctl -n hw.ncpu)
else
    CORES=$(nproc)
fi
echo "Detected $CORES cores for building."

echo "=== Starting Checkout and Build Process (Minimal) ==="
echo "Script Directory: $SCRIPT_DIR"

# ==========================================
# 1. CertCheck (Standalone)
# ==========================================
echo ""
echo ">>> Processing CertCheck (Standalone)..."
if [ -d "$SCRIPT_DIR/certcheck_tool" ]; then
    echo "CertCheck directory already exists in $SCRIPT_DIR/certcheck_tool. Skipping."
else
    echo "Downloading CertCheck..."
    cd "$TEMP_DIR"
    mkdir -p certcheck-1.0.1
    cd certcheck-1.0.1
    curl -L -o ../certcheck-1.0.1.tar.gz https://fmv.jku.at/certcheck/certcheck-1.0.1.tar.gz
    tar -xf ../certcheck-1.0.1.tar.gz
    
    echo "Patching CertCheck..."
    cp "$SCRIPT_DIR/certcheck_fix.patch" .
    patch -p0 < certcheck_fix.patch
    
    echo "Building CertCheck..."
    # Explicitly use gcc as makefile might default to cc which is clang on mac
    gcc -O3 -W -Wall -Wextra -Wunused -DNDEBUG -c simpleaig.c -o simpleaig.o
    gcc -O3 -W -Wall -Wextra -Wunused -DNDEBUG certcheck.c -o certcheck simpleaig.o
    
    echo "Installing CertCheck..."
    cd ../..
    # Move the entire directory to checkers/certcheck_tool
    mv "$TEMP_DIR/certcheck-1.0.1" "$SCRIPT_DIR/certcheck_tool"
    
    # Create symlink/copy for the binary in checkers root as requested
    ln -sf "$SCRIPT_DIR/certcheck_tool/certcheck" "$SCRIPT_DIR/certcheck"
    
    echo "CertCheck installed successfully."
fi

# ==========================================
# 2. CAQE (Solver + Certification Tool)
# ==========================================
echo ""
echo ">>> Processing CAQE..."
if [ -d "$SCRIPT_DIR/caqe_tool" ]; then
    echo "CAQE directory already exists in $SCRIPT_DIR/caqe_tool. Skipping."
else
    echo "Downloading CAQE..."
    cd "$SCRIPT_DIR/$TEMP_DIR"
    curl -L -o caqe-2.tar.gz https://finkbeiner.groups.cispa.de/tools/caqe/downloads/caqe-2.tar.gz
    tar -xf caqe-2.tar.gz
    
    cd caqe-2
    echo "Patching CAQE CertCheck..."
    cp "$SCRIPT_DIR/caqe_certcheck_fix.patch" .
    patch -p0 < caqe_certcheck_fix.patch
    
    echo "Building CAQE Solver..."
    ./configure
    make -j"$CORES"
    
    echo "Building CAQE CertCheck..."
    make -j"$CORES" certification
    
    cd ..
    echo "Installing CAQE..."
    mv caqe-2 "$SCRIPT_DIR/caqe_tool"
    
    # Link binaries to root
    ln -sf "$SCRIPT_DIR/caqe_tool/caqe" "$SCRIPT_DIR/caqe"
    ln -sf "$SCRIPT_DIR/caqe_tool/certcheck" "$SCRIPT_DIR/caqe_certcheck"
    
    echo "CAQE installed successfully."
fi

# ==========================================
# 3. Manthan (Dependencies for checkSkolem.py)
# ==========================================
echo ""
echo ">>> Processing Manthan (ABC & Python Env)..."
if [ -d "$SCRIPT_DIR/manthan" ]; then
    echo "Manthan directory already exists in $SCRIPT_DIR/manthan. Skipping."
else
    echo "Downloading Manthan..."
    cd "$SCRIPT_DIR/$TEMP_DIR"
    curl -L -o master.zip https://github.com/meelgroup/manthan/archive/refs/heads/master.zip
    unzip -q master.zip
    # Move to final location
    mv manthan-master "$SCRIPT_DIR/manthan"
    
    cd "$SCRIPT_DIR/manthan"
    
    echo "Cloning ABC (Minimal Dependency)..."
    # Extract ABC URL and Revision from dependency_pins.json
    ABC_INFO=$(python3 -c '
import json
try:
    with open("dependencies/dependency_pins.json") as f:
        pins = json.load(f)
    for p in pins:
        if "dependencies/abc" == p["path"]:
            print(f"{p["url"]} {p["rev"]}")
            break
except Exception as e:
    print("")
')
    
    ABC_URL=$(echo "$ABC_INFO" | cut -d' ' -f1)
    ABC_REV=$(echo "$ABC_INFO" | cut -d' ' -f2)
    
    if [ -z "$ABC_URL" ]; then
        echo "Error: Could not find ABC dependency in pins file."
        exit 1
    fi
    
    echo "Cloning ABC from $ABC_URL @ $ABC_REV"
    mkdir -p dependencies/abc
    git clone "$ABC_URL" dependencies/abc
    cd dependencies/abc
    git checkout "$ABC_REV"
    
    echo "Building ABC and helpers..."
    make clean || true
    FLAGS="-Wno-narrowing"
    # Build libabc.a first
    CC=g++ CXX=g++ CFLAGS="$FLAGS" CXXFLAGS="$FLAGS" make -j"$CORES" libabc.a
    
    # Build ABC helpers (file_generation_cex, file_generation_cnf, file_write_verilog)
    if [ -f file_generation_cex.c ] && [ -f file_generation_cnf.c ] && [ -f file_write_verilog.c ]; then
        echo "Building file_generation_cex..."
        g++ -Wall -g $FLAGS -c file_generation_cex.c -o file_generation_cex.o
        g++ -g -o file_generation_cex file_generation_cex.o libabc.a -lm -ldl -lreadline -lpthread
        
        echo "Building file_generation_cnf..."
        g++ -Wall -g $FLAGS -c file_generation_cnf.c -o file_generation_cnf.o
        g++ -g -o file_generation_cnf file_generation_cnf.o libabc.a -lm -ldl -lreadline -lpthread
        
        echo "Building file_write_verilog..."
        g++ -Wall -g $FLAGS -c file_write_verilog.c -o file_write_verilog.o
        g++ -g -o file_write_verilog file_write_verilog.o libabc.a -lm -ldl -lreadline -lpthread
        
        echo "Copying helpers to static_bin..."
        mkdir -p ../static_bin
        cp file_generation_cex file_generation_cnf file_write_verilog ../static_bin/
    else
        echo "Error: ABC helper source files not found"
        exit 1
    fi
    
    cd ../..

    echo "Patching checkSkolem.py..."
    cp "$SCRIPT_DIR/checkSkolem_fix.patch" .
    patch -p0 < checkSkolem_fix.patch
    
    echo "Setting up Python Environment..."
    
    echo "Setting up Python Environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create wrapper
    echo "Creating checkSkolem wrapper..."
    cat > "$SCRIPT_DIR/checkSkolem" <<EOF
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
export PYTHONPATH="\$SCRIPT_DIR/manthan"
source "\$SCRIPT_DIR/manthan/venv/bin/activate"
python "\$SCRIPT_DIR/manthan/checkSkolem.py" "\$@"
EOF
    chmod +x "$SCRIPT_DIR/checkSkolem"
    
    echo "Manthan setup complete."
fi

# ==========================================
# Cleanup
# ==========================================
echo ""
echo "Cleaning up..."
cd "$SCRIPT_DIR"
# Remove binaries if they were copied directly in previous versions, so symlinks can replace them
if [ -f "caqe" ] && [ ! -L "caqe" ]; then rm caqe; fi
if [ -f "certcheck" ] && [ ! -L "certcheck" ]; then rm certcheck; fi
if [ -f "caqe_certcheck" ] && [ ! -L "caqe_certcheck" ]; then rm caqe_certcheck; fi

rm -rf "$TEMP_DIR"

echo "=== Done! ==="
echo "Binaries:"
ls -l caqe caqe_certcheck certcheck checkSkolem
