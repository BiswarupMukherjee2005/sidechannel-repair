"""Stage 1: Side-channel leakage detection using simulation and TVLA."""


def run(*args, **kwargs):
    from .detect import run as _run
    return _run(*args, **kwargs)


__all__ = ["run"]
