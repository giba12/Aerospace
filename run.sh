#!/usr/bin/env bash
# One-command runner for sensor-sim: sets up Python, builds the simulator, runs the reference
# scenario, and leaves the results in ./out. Run it from anywhere:
#
#   ./run.sh              build (first time only) and run the reference scenario
#   ./run.sh --test       also build and run the whole test suite first
#   ./run.sh --clean      delete the build, the Python environment and ./out, then run
#   ./run.sh -- ARGS...   pass ARGS to the simulator, e.g. ./run.sh -- --sigma 2 --seed 7
#
# This is an educational simulation, not flight software (SYS-006).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

run_tests=0
clean=0
sim_args=(--steps 1000)
while [ $# -gt 0 ]; do
  case "$1" in
    --test)  run_tests=1 ;;
    --clean) clean=1 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --) shift; sim_args=("$@"); break ;;
    *) echo "run.sh: unknown option '$1' (try --help)" >&2; exit 2 ;;
  esac
  shift
done

die() { echo "run.sh: $*" >&2; exit 1; }

missing=()
for tool in cmake ninja python3; do
  command -v "$tool" >/dev/null || missing+=("$tool")
done
command -v g++ >/dev/null || command -v clang++ >/dev/null || missing+=("g++ or clang++")
if [ ${#missing[@]} -gt 0 ]; then
  echo "run.sh: missing tools: ${missing[*]}" >&2
  echo "On Ubuntu/Debian/WSL: sudo apt-get install -y g++ cmake ninja-build python3 python3-venv" >&2
  echo "No toolchain wanted? Use the container instead: see README, 'In a container'." >&2
  exit 1
fi
python3 -c 'import venv, ensurepip' 2>/dev/null \
  || die "python3 has no 'venv' module. On Ubuntu/Debian/WSL: sudo apt-get install -y python3-venv"

if [ "$clean" = 1 ]; then
  echo "==> Cleaning"
  rm -rf .venv build build-run out
fi

echo "==> Python environment (.venv)"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
# The stamp records which requirements file was installed, so pip only runs when it changes.
req_hash=$(sha256sum python/requirements.txt | cut -d' ' -f1)
if [ "$(cat .venv/.requirements-sha256 2>/dev/null || true)" != "$req_hash" ]; then
  .venv/bin/pip install --quiet -r python/requirements.txt
  echo "$req_hash" > .venv/.requirements-sha256
fi
export MPLCONFIGDIR="${MPLCONFIGDIR:-$PWD/.venv/matplotlib-cache}"

if [ "$run_tests" = 1 ]; then
  echo "==> Building with tests (build/; first time downloads GoogleTest)"
  cmake -S . -B build -G Ninja >/dev/null
  cmake --build build
  echo "==> Running the test suite"
  (cd build && ctest --output-on-failure)
  sim=build/sim
else
  # No tests means no GoogleTest download: this path needs the network only for pip.
  echo "==> Building the simulator (build-run/)"
  cmake -S . -B build-run -G Ninja -DSIM_BUILD_TESTS=OFF >/dev/null
  cmake --build build-run
  sim=build-run/sim
fi

echo "==> Running the simulator"
mkdir -p out
"./$sim" "${sim_args[@]}" --out out/run.csv

echo "==> Analyzing"
.venv/bin/python python/analyze.py out/run.csv --metrics-json out/metrics.json --plot out/plot.png

echo "==> Cross-check against the independent Python re-computation"
.venv/bin/python python/kalman_oracle.py out/run.csv

echo
echo "Done. Results are in: $PWD/out"
echo "  run.csv  run.csv.config.json  metrics.json  plot.png"
