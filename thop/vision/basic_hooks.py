import argparse
import logging
from .counter import (
    counter_parameters,
    counter_conv,
    counter_norm,
    counter_relu,
    counter_softmax,
    counter_avgpool,
    counter_adap_avg,
    counter_zero_ops,
    counter_upsample,
    counter_linear,
)
import torch
import torch.nn as nn
from torch.nn.modules.conv import _ConvNd

multiply_adds = 1


def count_parameters(m, x, y):
    total_params = 0
    for p in m.parameters():
        total_params += torch.DoubleTensor([p.numel()])
    m.total_params[0] = counter_parameters(m.parameters())


def zero_ops(m, x, y):
    m.total_ops += counter_zero_ops()


def count_convNd(m: _ConvNd, x: (torch.Tensor,), y: torch.Tensor):
    x = x[0]

    kernel_ops = torch.zeros(m.weight.size()[2:]).numel()  # Kw x Kh
    bias_ops = 1 if m.bias is not None else 0

    # N x Cout x H x W x  (Cin x Kw x Kh + bias)
    m.total_ops += counter_conv(
        bias_ops,
        torch.zeros(m.weight.size()[2:]).numel(),
        y.nelement(),
        m.in_channels,
        m.groups,
    )

    m.total_acts += y.nelement()


def count_convNd_ver2(m: _ConvNd, x: (torch.Tensor,), y: torch.Tensor):
    x = x[0]

    # N x H x W (exclude Cout)
    output_size = torch.zeros((y.size()[:1] + y.size()[2:])).numel()
    # # Cout x Cin x Kw x Kh
    # kernel_ops = m.weight.nelement()
    # if m.bias is not None:
    #     # Cout x 1
    #     kernel_ops += + m.bias.nelement()
    # # x N x H x W x Cout x (Cin x Kw x Kh + bias)
    # m.total_ops += torch.DoubleTensor([int(output_size * kernel_ops)])
    m.total_ops += counter_conv(m.bias.nelement(), m.weight.nelement(), output_size)


def count_bn(m, x, y):
    x = x[0]
    if not m.training:
        m.total_ops += counter_norm(x.numel())


def count_ln(m, x, y):
    x = x[0]
    if not m.training:
        m.total_ops += counter_norm(x.numel())


def count_in(m, x, y):
    x = x[0]
    if not m.training:
        m.total_ops += counter_norm(x.numel())


def count_prelu(m, x, y):
    x = x[0]

    nelements = x.numel()
    if not m.training:
        m.total_ops += counter_relu(nelements)


def count_relu(m, x, y):
    x = x[0]

    nelements = x.numel()

    m.total_ops += counter_relu(nelements)


def count_softmax(m, x, y):
    x = x[0]
    nfeatures = x.size()[m.dim]
    batch_size = x.numel() // nfeatures

    m.total_ops += counter_softmax(batch_size, nfeatures)


def count_avgpool(m, x, y):
    # total_add = torch.prod(torch.Tensor([m.kernel_size]))
    # total_div = 1
    # kernel_ops = total_add + total_div
    num_elements = y.numel()
    m.total_ops += counter_avgpool(num_elements)
    m.total_acts += num_elements


def count_adap_avgpool(m, x, y):
    kernel = torch.DoubleTensor([*(x[0].shape[2:])]) // torch.DoubleTensor(
        [*(y.shape[2:])]
    )
    total_add = torch.prod(kernel)
    num_elements = y.numel()
    m.total_ops += counter_adap_avg(total_add, num_elements)
    m.total_acts += num_elements


# TODO: verify the accuracy
def count_upsample(m, x, y):
    if m.mode not in (
        "nearest",
        "linear",
        "bilinear",
        "bicubic",
    ):  # "trilinear"
        logging.warning("mode %s is not implemented yet, take it a zero op" % m.mode)
        return counter_zero_ops()

    if m.mode == "nearest":
        return counter_zero_ops()

    x = x[0]
    m.total_ops += counter_upsample(m.mode, y.nelement())


# nn.Linear
def count_linear(m, x, y):
    # per output element
    total_mul = m.in_features
    # total_add = m.in_features - 1
    # total_add += 1 if m.bias is not None else 0
    num_elements = y.numel()

    m.total_ops += counter_linear(total_mul, num_elements)

    m.total_acts += num_elements
