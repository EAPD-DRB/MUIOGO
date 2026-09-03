"""Live convergence bar for OG-Core solves.

OG-Core's TPI / SS-inner loops iterate until the reported distance drops below a
threshold (mindist_TPI / mindist_SS); this turns that 'Distance:' stream into a
progress bar (log-space % of the way + an iters-left estimate). The SS *outer*
root-find has no single distance-vs-threshold, so no bar shows during it.
"""
from __future__ import annotations

import contextlib
import math
import re
import sys


class SolveProgress:
    _NOISE = ("Iteration:", "Distance:", "Maximum debt ratio", "K_d has negative",
              "w diff", "r diff", "r_p diff", "p_m diff", "BQ diff", "TR diff",
              "RM diff", "Y diff")
    _IT1 = re.compile(r"Iteration:\s*1\s*$")
    _DIST = re.compile(r"Distance:\s*([0-9.eE+-]+)")

    def __init__(self, stream, threshold, quiet=True, label="solve"):
        self.s, self.thr, self.quiet, self.label = stream, float(threshold), quiet, label
        self.start = self.prev = None
        self.it = 0
        self._buf = ""

    def write(self, text):
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._line(line)

    def _line(self, line):
        if self._IT1.search(line.strip()):
            self.start = self.prev = None
            self.it = 0
        m = self._DIST.search(line)
        if m:
            self._bar(float(m.group(1)))
            if not self.quiet:
                self.s.write(line + "\n")
            return
        low = line.lower()
        if (self.quiet and any(k in line for k in self._NOISE)
                and not any(b in low for b in ("error", "warn", "traceback", "fail"))):
            return
        self.s.write(line + "\n")

    def _bar(self, d):
        if self.start is None or d > self.start * 1.5:
            self.start, self.it = d, 0
        self.it += 1
        hi, lo = math.log10(self.start), math.log10(self.thr)
        frac = 1.0 if hi <= lo else max(0.0, min(1.0, (hi - math.log10(max(d, 1e-300))) / (hi - lo)))
        eta = ""
        if self.prev and 0 < d < self.prev and d > self.thr:
            eta = f" | ~{max(0, round(math.log(self.thr / d) / math.log(d / self.prev)))} left"
        self.prev = d
        fill = int(frac * 20)
        self.s.write(f"  [{self.label}] it{self.it:>3} | dist {d:.2e} -> thr {self.thr:.0e} "
                     f"| [{'#' * fill}{'.' * (20 - fill)}] {frac * 100:3.0f}%{eta}\n")
        self.s.flush()

    def flush(self):
        self.s.flush()

    def __getattr__(self, name):
        return getattr(self.s, name)


@contextlib.contextmanager
def solve_progress(threshold, label="solve", enabled=True, quiet=True):
    if not enabled:
        yield
        return
    real = sys.stdout
    sys.stdout = SolveProgress(real, threshold, quiet=quiet, label=label)
    try:
        yield
    finally:
        sys.stdout.flush()
        sys.stdout = real
