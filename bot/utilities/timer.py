import asyncio


class Timer:
    def __init__(self, timeout, callback, parameter=None):
        self._timeout = timeout
        self._callback = callback
        self._parameters = parameter
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback(self._parameters)

    def cancel(self):
        self._task.cancel()
