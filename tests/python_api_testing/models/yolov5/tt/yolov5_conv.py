import torch
import tt_lib

from loguru import logger
from tt_lib.fallback_ops import fallback_ops
from python_api_testing.models.utility_functions_new import (
    torch2tt_tensor,
    tt2torch_tensor,
)
from python_api_testing.models.conv_on_device_utils_new import (
    run_conv_on_tt_device,
    run_conv_on_device_wrapper,
    is_conv_supported_on_device,
)


def autopad(k, p=None, d=1):  # kernel, padding, dilation
    # Pad to 'same' shape outputs
    if d > 1:
        k = (
            d * (k - 1) + 1 if isinstance(k, int) else [d * (x - 1) + 1 for x in k]
        )  # actual kernel-size
    if p is None:
        p = k // 2 if isinstance(k, int) else [x // 2 for x in k]  # auto-pad
    return p


class TtYolov5Conv2D(torch.nn.Module):
    def __init__(
        self,
        state_dict,
        base_address,
        device,
        c1,
        c2,
        k=1,
        s=1,
        p=None,
        g=1,
        d=1,
    ):
        super().__init__()

        self.conv_weight = state_dict[f"{base_address}.weight"]
        bias_key = f"{base_address}.bias"

        if bias_key in state_dict:
            self.conv_bias = state_dict[bias_key]
        else:
            self.conv_bias = None

        if p is None:
            p = autopad(k, p, d)

        self.device = device
        self.host = tt_lib.device.GetHost()
        self.conv_on_device = True

        # conv_params = [out_channels, in_channels, kernel_size, kernel_size, stride, stride, padding, padding, dilation, groups]
        self.conv_params = [c2, c1, k, k, s, s, p, p, d, g]

        if self.conv_on_device and is_conv_supported_on_device(self.conv_params):
            self.conv_bias = self.conv_bias.unsqueeze(-1).unsqueeze(-1)

            logger.debug(f"Using TtConv for params {self.conv_params}")
            logger.debug(f"conv_weight shape {self.conv_weight.shape}")
            logger.debug(f"conv_bias shape {self.conv_bias.shape}")

            self.conv = run_conv_on_device_wrapper(
                self.conv_weight.reshape(-1).tolist(),
                self.conv_params,
                self.device,
                self.host,
                conv_bias=None,
            )

        else:
            self.conv_on_device = False
            logger.debug(f"Using fallback_ops.Conv2d for params {self.conv_params}")

            # self.conv = nn.Conv2d(c1, c2, k, s, padding, groups=g, dilation=d, bias=False)
            self.conv = fallback_ops.Conv2d(
                weights=self.conv_weight,
                biases=self.conv_bias,
                in_channels=c1,
                out_channels=c2,
                kernel_size=k,
                stride=s,
                padding=p,
                groups=g,
                dilation=d,
                bias=self.conv_bias is not None,
            )

    def forward(self, x):
        if self.conv_on_device:
            x = tt2torch_tensor(x)
            x = self.conv(x)
            x = x + self.conv_bias
            x = torch2tt_tensor(
                x, self.device, tt_layout=tt_lib.tensor.Layout.ROW_MAJOR
            )
        else:
            x = self.conv(x)

        return x


class TtYolov5Conv(torch.nn.Module):
    # Standard convolution with args(ch_in, ch_out, kernel, stride, padding, groups, dilation, activation)

    def __init__(
        self,
        state_dict,
        base_address,
        device,
        c1,
        c2,
        k=1,
        s=1,
        p=None,
        g=1,
        d=1,
        act=True,
    ):
        super().__init__()

        self.device = device
        self.conv = TtYolov5Conv2D(
            state_dict, f"{base_address}.conv", device, c1, c2, k, s, p, g, d
        )

        # self.act = self.default_act if act is True else act if isinstance(act, nn.Module) else nn.Identity()
        self.act = act

    def forward(self, x):
        x = self.conv(x)

        if self.act is True:
            x = fallback_ops.silu(x)
        else:
            # self.act if isinstance(self.act, nn.Module) else nn.Identity()
            assert False  # Not implemented

        return x
