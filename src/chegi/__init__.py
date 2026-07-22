"""cheGi — The ultimate Git companion. Type less, do more."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("chegi")
except PackageNotFoundError:
    __version__ = "0.0.0"
