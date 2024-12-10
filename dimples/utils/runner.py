# -*- coding: utf-8 -*-

from threading import Thread

from startrek.skywalker import Runner


# noinspection PyAbstractClass
class PatchRunner(Runner):

    @classmethod
    def thread_run(cls, runner: Runner) -> Thread:
        thr = Runner.async_thread(coro=_bg_runner(runner=runner))
        thr.start()
        return thr


async def _bg_runner(runner: Runner):
    # await runner.start()
    await runner.run()


# Patch for Runner
Runner.thread_run = PatchRunner.thread_run
