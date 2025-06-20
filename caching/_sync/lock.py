import threading
from typing import DefaultDict
from collections import defaultdict

_SYNC_LOCKS: DefaultDict[str, DefaultDict[str, threading.Lock]] = defaultdict(lambda: defaultdict(threading.Lock))
