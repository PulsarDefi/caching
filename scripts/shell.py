import IPython
from traitlets.config import Config


def shell():
    CONFIG = Config()
    CONFIG.TerminalInteractiveShell.autoindent = False

    IPython.start_ipython(config=CONFIG)


if __name__ == "__main__":
    shell()
