# SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.

# SPDX-License-Identifier: Apache-2.0

from typing import Tuple, Union


import tt_lib as ttl

import ttnn


def _torch_std(input_tensor: ttnn.Tensor, dim: int, keepdim=False, **_):
    import torch

    input_tensor = ttnn.from_device(input_tensor)
    input_tensor = ttnn.to_layout(input_tensor, ttnn.ROW_MAJOR_LAYOUT)
    input_tensor = ttnn.to_torch(input_tensor)

    return torch.std(input_tensor, dim=dim, keepdim=keepdim)


def _std_validate_input_tensors(operation_name, input_tensor, *args, **kwargs):
    ttnn.validate_input_tensor(
        operation_name,
        input_tensor,
        ranks=(2, 3, 4),
        dtypes=(ttnn.bfloat16, ttnn.bfloat8_b),
        layouts=(ttnn.TILE_LAYOUT,),
        can_be_on_device=True,
        can_be_on_cpu=False,
    )


@ttnn.register_operation(
    name="ttnn.std",
    validate_input_tensors=_std_validate_input_tensors,
    torch_function=_torch_std,
)
def std(
    input_tensor: ttnn.Tensor,
    dim: Union[int, Tuple[int]],
    keepdim: bool = False,
    memory_config: ttnn.MemoryConfig = ttnn.DRAM_MEMORY_CONFIG,
) -> ttnn.Tensor:
    """
    std(input_tensor: ttnn.Tensor, dim: Union[int, Tuple[int]], keepdim: bool = False) -> ttnn.Tensor
    """

    input_shape = tuple(input_tensor.shape)
    rank = len(input_shape)

    if isinstance(dim, int):
        if dim < 0:
            dim = rank + dim
        dim = (dim,)

    if isinstance(dim, tuple):
        if dim == (rank - 1,):
            reduce_op_dim = ttl.tensor.ReduceOpDim.W
        elif dim == (rank - 2,):
            reduce_op_dim = ttl.tensor.ReduceOpDim.H
        elif dim == (rank - 1, rank - 2):
            reduce_op_dim = ttl.tensor.ReduceOpDim.HW
        else:
            raise RuntimeError("Unsupported dim")
    else:
        raise RuntimeError("Invalid dim")

    output_shape = []
    padded_output_shape = []
    for axis, size in enumerate(input_shape):
        if axis in dim:
            if keepdim:
                output_shape.append(1)
                padded_output_shape.append(ttnn.TILE_SIZE)
        else:
            output_shape.append(size)
            padded_output_shape.append(size)
    output_shape = tuple(output_shape)
    padded_output_shape = tuple(padded_output_shape)

    input_tensor = ttnn.unsqueeze_to_4D(input_tensor)
    ttl_input_tensor = input_tensor.value

    mean_tensor = ttl.tensor.reduce(ttl_input_tensor, ttl.tensor.ReduceOpMath.SUM, reduce_op_dim, 1 / input_shape[-1])
    mean_square_tensor = ttl.tensor.reduce(
        ttl.tensor.pow(ttl_input_tensor, 2.0), ttl.tensor.ReduceOpMath.SUM, reduce_op_dim, 1 / input_shape[-1]
    )
    std_tensor = ttl.tensor.sqrt(ttl.tensor.sub(mean_square_tensor, (ttl.tensor.pow(mean_tensor, 2.0))))

    output_tensor = ttnn.Tensor(std_tensor)
    output_tensor = ttnn.reshape(output_tensor, ttnn.Shape(output_shape, padded_output_shape))

    return output_tensor


def _torch_var(input_tensor: ttnn.Tensor, dim: int, keepdim=False, **_):
    import torch

    input_tensor = ttnn.from_device(input_tensor)
    input_tensor = ttnn.to_layout(input_tensor, ttnn.ROW_MAJOR_LAYOUT)
    input_tensor = ttnn.to_torch(input_tensor)

    return torch.var(input_tensor, dim=dim, keepdim=keepdim)


def _var_validate_input_tensors(operation_name, input_tensor, *args, **kwargs):
    ttnn.validate_input_tensor(
        operation_name,
        input_tensor,
        ranks=(2, 3, 4),
        dtypes=(ttnn.bfloat16, ttnn.bfloat8_b),
        layouts=(ttnn.TILE_LAYOUT,),
        can_be_on_device=True,
        can_be_on_cpu=False,
    )


@ttnn.register_operation(
    name="ttnn.var",
    validate_input_tensors=_var_validate_input_tensors,
    torch_function=_torch_var,
)
def var(
    input_tensor: ttnn.Tensor,
    dim: Union[int, Tuple[int]],
    keepdim: bool = False,
    memory_config: ttnn.MemoryConfig = ttnn.DRAM_MEMORY_CONFIG,
) -> ttnn.Tensor:
    """
    var(input_tensor: ttnn.Tensor, dim: Union[int, Tuple[int]], keepdim: bool = False) -> ttnn.Tensor
    """

    input_shape = tuple(input_tensor.shape)
    rank = len(input_shape)

    if isinstance(dim, int):
        if dim < 0:
            dim = rank + dim
        dim = (dim,)

    if isinstance(dim, tuple):
        if dim == (rank - 1,):
            reduce_op_dim = ttl.tensor.ReduceOpDim.W
        elif dim == (rank - 2,):
            reduce_op_dim = ttl.tensor.ReduceOpDim.H
        elif dim == (rank - 1, rank - 2):
            reduce_op_dim = ttl.tensor.ReduceOpDim.HW
        else:
            raise RuntimeError("Unsupported dim")
    else:
        raise RuntimeError("Invalid dim")

    output_shape = []
    padded_output_shape = []
    for axis, size in enumerate(input_shape):
        if axis in dim:
            if keepdim:
                output_shape.append(1)
                padded_output_shape.append(ttnn.TILE_SIZE)
        else:
            output_shape.append(size)
            padded_output_shape.append(size)
    output_shape = tuple(output_shape)
    padded_output_shape = tuple(padded_output_shape)

    input_tensor = ttnn.unsqueeze_to_4D(input_tensor)
    ttl_input_tensor = input_tensor.value

    mean_tensor = ttl.tensor.reduce(ttl_input_tensor, ttl.tensor.ReduceOpMath.SUM, reduce_op_dim, 1 / input_shape[-1])
    mean_square_tensor = ttl.tensor.reduce(
        ttl.tensor.pow(ttl_input_tensor, 2.0), ttl.tensor.ReduceOpMath.SUM, reduce_op_dim, 1 / input_shape[-1]
    )
    variance_tensor = ttl.tensor.sub(mean_square_tensor, ttl.tensor.pow(mean_tensor, 2.0))

    output_tensor = ttnn.Tensor(variance_tensor)
    output_tensor = ttnn.reshape(output_tensor, ttnn.Shape(output_shape, padded_output_shape))

    return output_tensor


__all__ = []