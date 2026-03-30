import os
import logging
import sys

from contextlib import contextmanager


def setup_logger(folder: str, file_name: str, add_debug: bool):
    log_formatter_file = logging.Formatter(
        "%(asctime)s [%(levelname)-5.5s] %(message)s"
    )
    log_formatter_console = logging.Formatter("[%(levelname)-5.5s] %(message)s")
    root_logger = logging.getLogger("worldweaver")
    if add_debug:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    if not os.path.isdir(folder):
        os.makedirs(
            folder,
            exist_ok=True,
        )

    root_logger.handlers.clear()

    file_handler = logging.FileHandler(os.path.join(folder, file_name), mode="w")
    file_handler.setFormatter(log_formatter_file)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter_console)
    root_logger.addHandler(console_handler)


logger = logging.getLogger("worldweaver")


@contextmanager
def stdout_redirected(to=os.devnull):
    """
    import os

    with stdout_redirected(to=filename):
        print("from Python")
        os.system("echo non-Python applications are also supported")
    """
    fd = sys.stdout.fileno()

    ##### assert that Python and C stdio write using the same file descriptor
    ####assert libc.fileno(ctypes.c_void_p.in_dll(libc, "stdout")) == fd == 1

    def _redirect_stdout(to):
        sys.stdout.close()  # + implicit flush()
        os.dup2(to.fileno(), fd)  # fd writes to 'to' file
        sys.stdout = os.fdopen(fd, "w")  # Python writes to fd

    with os.fdopen(os.dup(fd), "w") as old_stdout:
        with open(to, "w") as file:
            _redirect_stdout(to=file)
        try:
            yield  # allow code to be run with the redirected stdout
        finally:
            _redirect_stdout(to=old_stdout)  # restore stdout.
            # buffering and flags such as
            # CLOEXEC may be different
