import asyncio
from typing import Callable
import json


class FastSocket:
    def __init__(self, host: str = None, port: int = None, logfunc: Callable | None = print):

        if logfunc is None:
            def logfunc(msg):
                pass
        self.log = logfunc

        self._in_queue = asyncio.Queue()
        self._out_queue = asyncio.Queue()
        self.ack_pool = {}


        self.addr = self._build_addr(host, port) if host and port else None

    def _build_addr(self, host: str, port: int) -> str:
        return (host, port)

    def set_addr(self, host: str, port: int):
        self.addr = self._build_addr(host, port)