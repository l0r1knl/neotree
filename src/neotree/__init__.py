"""neotree — tree-compatible structure viewer with compact grouped output."""

__version__ = "0.1.0"


class NtreeError(Exception):
    """User-facing CLI error.

    Raised for invalid arguments, missing directories, and other
    recoverable input errors. The message is printed to stderr
    and the process exits with code 1.
    """
