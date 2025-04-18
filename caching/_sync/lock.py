import threading
from typing import DefaultDict
from collections import defaultdict

_SYNC_LOCKS: DefaultDict[int, DefaultDict[str, threading.Lock]] = defaultdict(lambda: defaultdict(threading.Lock))
