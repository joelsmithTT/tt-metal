# SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.

# SPDX-License-Identifier: Apache-2.0

import pytest
import torch
from loguru import logger

import tt_lib as ttl
from models.utility_functions import comp_allclose_and_pcc, skip_for_wormhole_b0

TILE_HEIGHT = 32
TILE_WIDTH = 32


def get_tensors(input_shape, output_shape, device, *, with_padding=True):
    npu_dtype = ttl.tensor.DataType.BFLOAT16
    cpu_dtype = torch.bfloat16
    npu_layout = ttl.tensor.Layout.TILE

    torch_input = torch.randint(-2, 3, input_shape, dtype=cpu_dtype, requires_grad=True)
    torch_output = torch.randint(-2, 3, output_shape, dtype=cpu_dtype)

    if with_padding:
        tt_input = ttl.tensor.Tensor(torch_input, npu_dtype).pad_to_tile(float("nan")).to(npu_layout).to(device)
        tt_output = ttl.tensor.Tensor(torch_output, npu_dtype).pad_to_tile(float("nan")).to(npu_layout).to(device)
    else:
        tt_input = ttl.tensor.Tensor(torch_input, npu_dtype).to(npu_layout).to(device)
        tt_output = ttl.tensor.Tensor(torch_output, npu_dtype).to(npu_layout).to(device)

    return tt_input, tt_output, torch_input


def get_backward_tensors(output_grad_shape, input_grad_shape, device, *, with_padding=True):
    npu_dtype = ttl.tensor.DataType.BFLOAT16
    cpu_dtype = torch.bfloat16
    npu_layout = ttl.tensor.Layout.TILE

    torch_output_grad = torch.randint(-2, 3, output_grad_shape, dtype=cpu_dtype, requires_grad=True)
    torch_input_grad = torch.randint(-2, 3, input_grad_shape, dtype=cpu_dtype)

    if with_padding:
        tt_output_grad = (
            ttl.tensor.Tensor(torch_output_grad, npu_dtype).pad_to_tile(float("nan")).to(npu_layout).to(device)
        )
        tt_input_grad = (
            ttl.tensor.Tensor(torch_input_grad, npu_dtype).pad_to_tile(float("nan")).to(npu_layout).to(device)
        )
    else:
        tt_output_grad = ttl.tensor.Tensor(torch_output_grad, npu_dtype).to(npu_layout).to(device)
        tt_input_grad = ttl.tensor.Tensor(torch_input_grad, npu_dtype).to(npu_layout).to(device)

    return tt_output_grad, tt_input_grad, torch_output_grad


@pytest.mark.parametrize(
    "input_shape",
    (([4, 4, TILE_HEIGHT * 12 - 1, TILE_WIDTH * 12 - 1]),),
    ids=[
        "4, 4, TILE_HEIGHT * 12 - 1, TILE_WIDTH * 12 - 1",
    ],
)
@pytest.mark.parametrize(
    "dims",
    (
        [0],
        [0, 1],
        [0, 1, 2],
        [0, 1, 2, 3],
        [0, 1, 3],
        [0, 2, 3],
        [1],
        [1, 2],
        [1, 2, 3],
        [1, 3],
        [2],
        [2, 3],
        [3],
    ),
    ids=["0", "0,1", "0,1,2", "0,1,2,3", "0,1,3", "0,2,3", "1", "1,2", "1,2,3", "1,3", "2", "2,3", "3"],
)
@pytest.mark.parametrize("use_provide_output", (True, False), ids=["True", "False"])
def test_moreh_sum(input_shape, dims, use_provide_output, device):
    torch.manual_seed(2023)
    output_shape = input_shape.copy()

    for dim in dims:
        output_shape[dim] = 1

    (tt_input, tt_output, torch_input) = get_tensors(input_shape, output_shape, device)

    if not use_provide_output:
        tt_output = None

    torch_output = torch.sum(torch_input, dims, True)

    cpu_layout = ttl.tensor.Layout.ROW_MAJOR
    tt_output_cpu = (
        ttl.operations.primary.moreh_sum(tt_input, dims=dims, output=tt_output)
        .cpu()
        .to(cpu_layout)
        .unpad_from_tile(output_shape)
        .to_torch()
    )

    # test for equivalance
    # TODO(Dongjin) : check while changing rtol after enabling fp32_dest_acc_en
    rtol = atol = 0.12
    passing, output_pcc = comp_allclose_and_pcc(torch_output, tt_output_cpu, pcc=0.999, rtol=rtol, atol=atol)

    logger.debug(f"Out passing={passing}")
    logger.debug(f"Output pcc={output_pcc}")

    assert passing


def reduce_rows(x, dims):
    index_tuple = tuple(slice(0, 1) if i in dims else slice(None) for i in range(x.dim()))
    return x[index_tuple]


@pytest.mark.parametrize(
    "input_shape",
    (
        ([TILE_HEIGHT, TILE_WIDTH]),
        ([TILE_HEIGHT * 3, TILE_WIDTH * 3]),
        ([4, TILE_HEIGHT * 2, TILE_WIDTH * 2]),
    ),
    ids=[
        "TILE_HEIGHT, TILE_WIDTH",
        "TILE_HEIGHT * 3, TILE_WIDTH * 3",
        "4, TILE_HEIGHT * 2, TILE_WIDTH * 2",
    ],
)
@pytest.mark.parametrize(
    "dims",
    (
        [0],
        [0, 1],
        [0, 1, 2],
        [0, 2],
        [1],
        [1, 2],
        [2],
    ),
    ids=["0", "0,1", "0,1,2", "0, 2", "1", "1,2", "2"],
)
def test_moreh_sum_non_4d(input_shape, dims, device):
    torch.manual_seed(2023)
    output_shape = input_shape.copy()

    input_rank = len(input_shape)
    for dim in dims:
        if dim >= input_rank:
            pytest.skip(f"input dim {dim} exceeds the dims of input tensor {len(input_shape)}.")

    (tt_input, _, torch_input) = get_tensors(input_shape, output_shape, device, with_padding=False)

    torch_output = torch.sum(torch_input, dims, True)
    cpu_layout = ttl.tensor.Layout.ROW_MAJOR
    tt_output_cpu = ttl.operations.primary.moreh_sum(tt_input, dims=dims, output=None).cpu().to(cpu_layout).to_torch()

    tt_output_cpu = reduce_rows(tt_output_cpu, dims)
    rtol = atol = 0.12
    passing, output_pcc = comp_allclose_and_pcc(torch_output, tt_output_cpu, pcc=0.999, rtol=rtol, atol=atol)

    logger.debug(f"Out passing={passing}")
    logger.debug(f"Output pcc={output_pcc}")

    assert passing


@pytest.mark.parametrize(
    "input_shape",
    (
        ([1, 1, TILE_HEIGHT - 1, TILE_WIDTH - 1]),
        ([4, 4, TILE_HEIGHT * 20 - 1, TILE_WIDTH * 20 - 1]),
    ),
    ids=[
        "1, 1, TILE_HEIGHT-1,TILE_WIDTH - 1",
        "4, 4, TILE_HEIGHT * 20 - 1, TILE_WIDTH * 20 - 1",
    ],
)
@pytest.mark.parametrize(
    "dims",
    (
        [0],
        [0, 1],
        [0, 1, 2],
        [0, 1, 2, 3],
        [0, 1, 3],
        [0, 2, 3],
        [1],
        [1, 2],
        [1, 2, 3],
        [1, 3],
        [2],
        [2, 3],
        [3],
    ),
    ids=["0", "0,1", "0,1,2", "0,1,2,3", "0,1,3", "0,2,3", "1", "1,2", "1,2,3", "1,3", "2", "2,3", "3"],
)
@pytest.mark.parametrize("use_provide_input_grad", (True, False), ids=["True", "False"])
def test_moreh_sum_backward(input_shape, dims, use_provide_input_grad, device):
    torch.manual_seed(2023)
    output_shape = input_shape.copy()

    for dim in dims:
        output_shape[dim] = 1

    (tt_input, _, torch_input) = get_tensors(input_shape, output_shape, device)
    (tt_output_grad, tt_input_grad, torch_output_grad) = get_backward_tensors(output_shape, input_shape, device)

    if not use_provide_input_grad:
        tt_input_grad = None

    torch_output = torch.sum(torch_input, dims, True)
    torch_output.backward(torch_output_grad)

    cpu_layout = ttl.tensor.Layout.ROW_MAJOR
    tt_input_grad_cpu = (
        ttl.operations.primary.moreh_sum_backward(tt_output_grad, tt_input, dims=dims, input_grad=tt_input_grad)
        .cpu()
        .to(cpu_layout)
        .unpad_from_tile(input_shape)
        .to_torch()
    )

    # test for equivalance
    rtol = atol = 0.1
    passing, output_pcc = comp_allclose_and_pcc(torch_input.grad, tt_input_grad_cpu, pcc=0.999, rtol=rtol, atol=atol)

    logger.debug(f"Out passing={passing}")
    logger.debug(f"Output pcc={output_pcc}")

    assert passing
