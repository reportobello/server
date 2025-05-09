import asyncio
import os
from collections.abc import Callable
from multiprocessing.pool import ThreadPool


class JobQueue(ThreadPool):
    def __init__(self) -> None:
        # See https://stackoverflow.com/a/55423170
        # This number can probably be optimized, but is good enough for now
        core_count = len(os.sched_getaffinity(0))

        super().__init__(core_count * 2)

    async def run[RType, **Args](
        self,
        f: Callable[Args, RType],
        *args: Args.args,
        **_: Args.kwargs,
    ) -> RType:
        task = self.apply_async(f, args)

        while not task.ready():  # noqa: ASYNC110
            await asyncio.sleep(0.01)

        return task.get()
