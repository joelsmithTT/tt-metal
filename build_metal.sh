#!/bin/bash
set -eo pipefail

if [ -z "$PYTHON_ENV_DIR" ]; then
    PYTHON_ENV_DIR=$(pwd)/python_env
fi

if [ -z "$CONFIG" ]; then
    echo "Build type defaulted to Release"
else
    VALID_CONFIGS="RelWithDebInfo Debug Release ci"
    if [[ $VALID_CONFIGS =~ (^|[[:space:]])"$CONFIG"($|[[:space:]]) ]]; then
        echo "CONFIG set to $CONFIG"
    else
        echo "Invalid config "$CONFIG" given.. Valid configs are: $VALID_CONFIGS"
        exit 1
    fi
fi

echo "Building tt-metal"
cmake -B build -G Ninja
cmake --build build --target install

./scripts/build_scripts/create_venv.sh

if [ "$CONFIG" != "ci" ]; then
    echo "Building cpp tests"
    cmake --build build --target tests -- -j`nproc`

    source $PYTHON_ENV_DIR/bin/activate
    echo "Generating stubs"
    stubgen -m tt_lib -m tt_lib.device -m tt_lib.profiler -m tt_lib.tensor -m tt_lib.operations -m tt_lib.operations.primary -m tt_lib.operations.primary.transformers -o tt_eager
    stubgen -p ttnn._ttnn -o ttnn
    sed -i 's/\._C/tt_lib/g' tt_eager/tt_lib/__init__.pyi
fi
