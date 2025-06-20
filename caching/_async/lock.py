import asyncio
from typing import DefaultDict
from collections import defaultdict

_ASYNC_LOCKS: DefaultDict[str, DefaultDict[str, asyncio.Lock]] = defaultdict(lambda: defaultdict(asyncio.Lock))
