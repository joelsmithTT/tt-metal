# SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.

# SPDX-License-Identifier: Apache-2.0

import pytest
from pathlib import Path
import sys
import torch

f = f"{Path(__file__).parent}"
sys.path.append(f"{f}/../..")
sys.path.append(f"{f}/..")

import numpy as np

import tt_lib as ttl
from models.utility_functions import tilize


@pytest.mark.parametrize(
    "nb, nc, nh, nw",
    (
        (5, 2, 4, 8),
        (5, 2, 4, 7),
        ## resnet shapes
        (1, 1, 784, 2),
        (8, 1, 2, 64),
        (1, 1, 1, 64),
    ),
)
@pytest.mark.parametrize(
    "multicore",
    (
        False,
        True,
    ),
)
def test_run_tilize_test(nb, nc, nh, nw, multicore, device):
    nt = nb * nc * nh * nw
    shape = [nb, nc, 32 * nh, 32 * nw]

    inp = np.random.rand(*shape)

    a = ttl.tensor.Tensor(
        inp.flatten().tolist(),
        shape,
        ttl.tensor.DataType.BFLOAT16,
        ttl.tensor.Layout.ROW_MAJOR,
        device,
    )
    b = ttl.tensor.tilize(a, use_multicore = multicore)
    c = b.cpu().to_torch().to(torch.float32).reshape(shape).numpy()

    tilized_inp = tilize(inp.reshape(*shape))

    assert (
        abs(tilized_inp - c) < 0.02
    ).all(), "Max abs difference for tilize can be 0.02 due to bfloat conversions"
