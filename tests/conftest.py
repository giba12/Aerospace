"""Shared pytest plumbing.

`@pytest.mark.req("SEN-004", ...)` is how a pytest test names the requirements it verifies
(TST-005). This hook copies the marker into the JUnit XML as a `requirements` property, which
is where tools/req_trace.py reads it.
"""
import os
import pathlib
import subprocess
import sys

import pytest


@pytest.fixture(autouse=True)
def _record_requirements(request, record_property):
    ids = [i for m in request.node.iter_markers("req") for i in m.args]
    if ids:
        record_property("requirements", ",".join(ids))


@pytest.fixture(scope="session")
def sim_bin():
    """Path to the built `sim` executable. CTest sets SIM_BIN; a bare `pytest` run fails loudly."""
    path = os.environ.get("SIM_BIN")
    if not path or not pathlib.Path(path).exists():
        pytest.fail("SIM_BIN is not set to an existing file; run the tests through `ctest`")
    return path


@pytest.fixture
def run_sim(sim_bin, tmp_path):
    """Run `sim` in a scratch directory and return the CompletedProcess."""
    def _run(*args):
        return subprocess.run([sim_bin, *args], cwd=tmp_path, capture_output=True, text=True)
    return _run
