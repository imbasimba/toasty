# -*- mode: python; coding: utf-8 -*-
# Copyright 2022 the AAS WorldWide Telescope project
# Licensed under the MIT License.

"""Utilities for progress reporting

This module provides an extremely thin wrapper around TQDM that avoids ``\r``
output when stdout is not a terminal, for producing more easily greppable logs.
It also reduces the update frequency to reduce log volume.

"""

__all__ = """
progress_bar
""".split()

from contextlib import contextmanager
import os
import sys

from tqdm import tqdm

NON_TTY_INTERVAL = 30


@contextmanager
def progress_bar(total=None, show=None):
    assert total is not None
    assert show is not None

    args = dict(
        total=total,
        disable=not show,
    )

    log_like_output = not sys.stdout.isatty() and "JPY_PARENT_PID" not in os.environ

    if log_like_output:
        args["bar_format"] = "{l_bar}{bar}{r_bar}\n"
        args["mininterval"] = NON_TTY_INTERVAL
        args["maxinterval"] = NON_TTY_INTERVAL

    try:
        with tqdm(**args) as progress:
            yield progress
    finally:
        if show and not log_like_output:
            print()
