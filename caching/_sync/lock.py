import threading
from collections import defaultdict
from typing import DefaultDict

_SYNC_LOCKS: DefaultDict[str, DefaultDict[str, threading.Lock]] = defaultdict(lambda: defaultdict(threading.Lock))
