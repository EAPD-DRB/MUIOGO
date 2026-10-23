"""oglink: a standalone orchestration layer coupling OG-Core (OLG macro) and
CLEWS/OSeMOSYS (least-cost energy-land-water LP).

Design principle: keep both models independently runnable; the
coupling is a separate layer that exchanges quantities forward and prices/duals back,
iterated to a fixed point.

Import-light by design: submodules are NOT imported here, so the pure-numpy channel
transforms (``channels``) and the dataclass contract (``contract``) stay usable without
pandas or ogcore. Import what you need, e.g. ``from oglink import channels``.
"""
__all__ = ["channels", "contract", "framework", "og_wedge", "report", "signals"]
__version__ = "0.1.0"
