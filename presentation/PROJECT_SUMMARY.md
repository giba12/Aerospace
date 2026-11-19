**sensor-sim: a sensor and Kalman-filter simulator built with systems-engineering rigor**

sensor-sim simulates an object moving in one dimension, produces seeded noisy position readings (5 m Gaussian noise), and estimates position and velocity from those readings alone with a linear Kalman filter. It then scores the estimate against the known truth. The truth is never given to the estimator, and a compile-time check (static_assert) enforces it.

**Results.** On the reference run the raw readings are off by 5.46 m RMSE and the filter's position estimate by 2.32 m (ratio 0.43). It recovers velocity, which the sensor never measures, to 1.2 m/s. Across 50 held-out seeds, never used for tuning, the worst ratio is 0.561 against a required 0.75, and 97.6% of true positions fall inside the filter's own ±2σ error bars, against a required 90%. The limits are reported too: with a truth accelerating at 0.5 m/s² the filter is no better than the raw readings.

**Design.** A C++17 library (Dynamics, NoisySensor, KalmanEstimator, Runner, CsvRecorder) sits behind small interfaces, so each part can be tested with fakes. The filter maths is two pure functions. Runs are deterministic: seeded RNG, 17-digit CSV, atomic file writes. Python tools analyze the output and cross-check the filter against an independent recomputation in 60-digit decimal arithmetic. The design is modelled in SysML: block, internal block, activity, state machine and requirements diagrams.

**Verification.** 70 requirements (61 Must), each traced to a test; CI fails if a Must loses its test. 215 automated tests (GoogleTest and pytest), 94% line coverage, AddressSanitizer and UBSan, GCC 13 and Clang 18, and a clean-room container build.

**Stack.** C++17, CMake and Ninja, GoogleTest, Python 3.12, matplotlib, pytest, gcovr, Docker or Podman, GitHub Actions.

An educational simulation, not flight software.
