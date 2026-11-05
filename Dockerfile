# A clean-room build of sensor-sim (baseline SYS-001 / VAL-01). Building this image builds the
# program from a fresh copy of the source, installs the pinned Python packages, and runs the WHOLE
# test suite inside the image, so an image that exists is an image whose tests passed.
# Podman builds it the same way: replace `docker` with `podman` in the commands below.
#
#   docker build -t sensor-sim .
#   mkdir -p out && docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/out:/out" sensor-sim
#
# With rootless Podman use `--userns=keep-id` instead of `--user ...`: otherwise the container's
# user is not the user that owns ./out and the run fails with "cannot open for writing".
#   podman build -t sensor-sim .
#   mkdir -p out && podman run --rm --userns=keep-id -v "$PWD/out:/out" sensor-sim
#
# The run writes run.csv, run.csv.config.json, metrics.json and plot.png into ./out and prints the
# metrics and the independent cross-check. Nothing here is a secret and nothing needs a network at
# run time; the build needs one (apt, pip and the GoogleTest download).
#
# This is an educational simulation, not flight software (SYS-006).

# Pinned by digest, not just by tag (NFR-009): Ubuntu 24.04 gives GCC 13.3, CMake 3.28, Python 3.12.
# The apt packages below are not individually pinned; the base image digest bounds what they can be.
FROM docker.io/library/ubuntu:24.04@sha256:78d4744ead1f5b19b04d0df558ab182a5300903900755e515b2ca4d10eb2044d

LABEL org.opencontainers.image.title="sensor-sim" \
      org.opencontainers.image.description="Educational sensor and Kalman-filter state-estimation simulation. Not flight software." \
      org.opencontainers.image.licenses="NOASSERTION"

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends g++ cmake ninja-build python3 python3-venv ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# /out is where a run leaves its files. The base image already has a non-root user `ubuntu` (uid 1000).
RUN mkdir /out /app && chown ubuntu:ubuntu /out /app
WORKDIR /app
USER ubuntu

# matplotlib wants a writable cache directory, and a user chosen with --user has no home.
ENV MPLCONFIGDIR=/tmp/matplotlib \
    PATH=/app/.venv/bin:$PATH

# The README's step 1. Only the requirements file is copied first, so editing the source does not
# repeat the package download.
COPY --chown=ubuntu:ubuntu python/requirements.txt python/requirements.txt
RUN python3 -m venv .venv && pip install --no-cache-dir -r python/requirements.txt

# The README's step 2.
COPY --chown=ubuntu:ubuntu . /app
RUN cmake -S . -B build -G Ninja -DSIM_WARNINGS_AS_ERRORS=ON && cmake --build build

# The README's step 3: the clean-room check. --build-arg RUN_TESTS=0 skips it for a quick demo.
ARG RUN_TESTS=1
RUN if [ "$RUN_TESTS" = "1" ]; then cd build && ctest --output-on-failure; fi

# The README's steps 4 and 5.
CMD ["sh", "-c", "./build/sim --steps 1000 --out /out/run.csv && python python/analyze.py /out/run.csv --metrics-json /out/metrics.json --plot /out/plot.png && python python/kalman_oracle.py /out/run.csv"]
