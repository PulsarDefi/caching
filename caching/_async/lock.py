import asyncio
from collections import defaultdict
from typing import DefaultDict

_ASYNC_LOCKS: DefaultDict[str, DefaultDict[str, asyncio.Lock]] = defaultdict(lambda: defaultdict(asyncio.Lock))
