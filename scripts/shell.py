import IPython
from traitlets.config import Config

"""
No use other than opening shell with ipython and test stuff
"""


def shell():
    CONFIG = Config()
    CONFIG.TerminalInteractiveShell.autoindent = False
    CONFIG.InteractiveShellApp.exec_lines = ["from caching import cache"]

    IPython.start_ipython(config=CONFIG)


if __name__ == "__main__":
    shell()
