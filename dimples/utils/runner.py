# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

import collections
from threading import Thread

from startrek.fsm import Runner


# noinspection PyAbstractClass
class PatchRunner(Runner):

    @classmethod
    def thread_run(cls, main: collections.Coroutine = None, runner: Runner = None):
        """ Run target in a background thread """
        if main is not None:
            thr = Thread(target=_start_coroutine, args=(main,), daemon=True)
        elif runner is not None:
            thr = Thread(target=_start_runner, args=(runner,), daemon=True)
        else:
            return None
        # start background thread
        thr.start()
        return thr


def _start_coroutine(coroutine: collections.Coroutine):
    Runner.sync_run(main=coroutine)


def _start_runner(runner: Runner):
    Runner.sync_run(main=_run_forever(runner=runner))


async def _run_forever(runner: Runner):
    await runner.start()
    interval = _get_interval(runner=runner, fast=Runner.INTERVAL_FAST, slow=(Runner.INTERVAL_SLOW * 2))
    while True:
        await Runner.sleep(seconds=interval)
        if not runner.running:
            break


def _get_interval(runner: Runner, fast: float = 0.1, slow: float = 1.0) -> float:
    interval = runner.interval * 2
    if interval < fast:
        return fast
    elif interval > slow:
        return slow
    else:
        return interval


# Patch for Runner
Runner.thread_run = PatchRunner.thread_run
