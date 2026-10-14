# 30-Day Aerospace and Defense Software Job Sprint

## Continuation brief for a new chat

Use this guide as the working context for continuing the project. The learner is pursuing a first job in or near the Colorado Springs aerospace, space, defense, simulation, and software ecosystem. They have about 30 days for an intensive sprint. They prefer plain-language instruction that starts at the beginner level and builds toward advanced concepts. **Explain the technical architecture, the reason for each component, and how data moves through the system before asking the learner to implement it.** Do not jump straight to code or assume unfamiliarity is a lack of ability. Teach, check understanding where useful, then build incrementally.

## 1. Outcome and strategy

The goal is not to master aerospace software engineering in a month. The goal is to become a credible candidate for junior or associate software, test, simulation, or systems-adjacent roles, while making a small, polished project that demonstrates engineering habits and a clear capacity to learn.

By the end of the sprint, aim to have:

- One buildable, documented C++ project with a working simulation and state-estimation demonstration.
- A Python analysis script that turns a run into understandable plots and summary metrics.
- Automated tests and a continuous-integration workflow that builds and tests the project.
- A reproducible run path using documented Linux commands and, if time permits, a container.
- A portfolio narrative and job-search materials that accurately describe what was built and what the learner understands.
- Applications and conversations underway throughout the month, not postponed until the project is “perfect.”

Suggested allocation: roughly 40% project work, 30% applications/networking, 20% interview preparation, and 10% portfolio and professional presentation. Treat this as a guide, not a rigid schedule. Keep applying while the project is in progress.

## 2. Project at a glance

**Project name:** Distributed Sensor and State-Estimation Simulator

**Core idea:** Simulate a moving object, generate imperfect sensor observations of its motion, estimate its hidden state with a Kalman filter, and compare the estimate with the known simulated truth.

```text
Dynamic System
      ↓
C++ Physics / Simulation Engine
      ↓
True State (position, velocity, time)
      ↓
Sensor Model (sampling and measurement noise)
      ↓
Noisy Measurements
      ↓
State Estimator (Kalman filter)
      ↓
Estimated State and uncertainty
      ↓
Python analysis, plots, and error metrics
```

This is a **local, single-process prototype** first. “Distributed” is a future design direction: the initial project should model distinct components and data contracts without adding network services, message brokers, or deployment complexity. This keeps the first version achievable and makes the architecture easier to explain.

## 3. Architecture, explained before coding

The simulation creates a **ground truth**: the state the simulated object actually has at each time step. A state can begin with position and velocity; acceleration can be included as an input or later as part of the state. The simulator advances the state in fixed time increments using a numerical integration method.

The sensor model receives the true state but does not reveal it perfectly. It samples at a chosen rate and adds noise to measurements, such as position. Noise should be generated reproducibly from a configurable random seed so two runs can be compared. A sensor reading should carry a timestamp and clearly named measurement values.

The estimator receives only measurements and the system model. A Kalman filter keeps an estimated state and an uncertainty description. In each cycle it predicts the next state, then corrects that prediction using the new measurement. It should not receive the true state; the simulator keeps truth separate so the evaluation is meaningful.

The C++ program coordinates the time loop and writes results in a simple documented format such as CSV. Python reads that output, computes metrics such as root mean squared error (RMSE), and plots truth, measurements, and estimates. This boundary makes each side easy to understand: C++ handles the simulation loop, while Python supports analysis and presentation.

### Data ownership and flow

At each time step, the runner owns the sequence of operations: advance or query the truth, ask the sensor for an observation when it is due, pass that observation to the estimator, and record the outputs. Use small value-like structures for state, measurement, and estimate data. Avoid global mutable state. Keep the true state out of the estimator interface.

### First model choice

Start with a one-dimensional constant-velocity model. It is enough to demonstrate prediction, noisy measurements, and correction without requiring advanced orbital mechanics. Use position and velocity as the state, with optional acceleration as a known input. Once this end-to-end path works, add a two-dimensional model if time permits. Describe it honestly as a physics-inspired tracking simulation, not a high-fidelity orbital simulator.

## 4. Technology choices and scope

- **C++ (primary):** simulation, sensor, estimator, and orchestration. Use modern C++ features where they make ownership and types clear; do not add abstractions just to display language features.
- **Python:** analysis, plotting, and experiment comparison. Keep it out of the core simulation initially.
- **CMake:** configure and build the C++ project consistently.
- **GoogleTest or Catch2:** select one test framework and use it consistently. A minimal dependency setup is preferable to spending days on build plumbing.
- **Git:** make small commits with clear messages and keep the README current.
- **Linux:** practice the normal development loop: configure, build, test, run, inspect output, and debug.
- **CI:** automate configure/build/test on pushes and pull requests using a mainstream hosted CI service.
- **Docker or Podman (optional core extension):** document a reproducible environment after the local build works. Do not let the container block the simulation.

Keep the first scope narrow. Defer Kubernetes, Kafka, CUDA, machine learning, web interfaces, and real-time networking unless a target role specifically calls for them and the core project is already complete.

## 5. Repository layout

```text
distributed-sensor-simulator/
├── CMakeLists.txt
├── README.md
├── LICENSE                         # choose an appropriate license if publishing
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── include/
│   └── simulator/
│       ├── state.hpp
│       ├── sensor.hpp
│       ├── estimator.hpp
│       └── simulation.hpp
├── src/
│   ├── main.cpp
│   ├── sensor.cpp
│   ├── estimator.cpp
│   └── simulation.cpp
├── tests/
│   ├── CMakeLists.txt
│   ├── sensor_tests.cpp
│   ├── estimator_tests.cpp
│   └── simulation_tests.cpp
├── python/
│   ├── analyze.py
│   └── requirements.txt
├── docs/
│   ├── architecture.md
│   └── learning-notes.md
├── data/                            # small example output only, if useful
└── Dockerfile                       # optional; add after local build works
```

The exact filenames can change as the design becomes clearer. Keep interfaces small and avoid creating empty layers merely to match this diagram.

## 6. Thirty-day learning and implementation sequence

### Days 1–3: orient and establish the workflow

Explain the architecture in plain language and sketch the data flow before writing simulation code. Confirm the machine has a usable C++ compiler, CMake, Git, and Python. Create the repository, README outline, and a tiny C++ executable that builds through CMake. Practice the edit → build → run → inspect → commit cycle.

**Milestone:** a clean repository with a documented build command and a working “hello” executable.

### Days 4–7: C++ foundations through the project

Learn the C++ concepts as they appear: structs/classes, references and `const`, standard containers, functions, header/source separation, RAII, and basic error handling. Do not memorize broad topic lists before using them. Add a `State` type and a simple deterministic state update.

**Milestone:** the program advances a one-dimensional state through several time steps and prints or saves the results.

### Days 8–11: dynamics and numerical integration

Define the motion model and time step. Implement Euler integration first because it is easy to reason about. Compare against an analytic constant-velocity case. If the core is stable, add RK4 only where it teaches something useful; for constant velocity it may be unnecessary. Record assumptions and units.

**Milestone:** repeatable truth data with a documented model, time step, and units.

### Days 12–15: sensor model

Add measurement sampling and configurable noise. Use a fixed random seed in example runs. Keep measurements distinct from true state and include timestamps. Write tests for sampling cadence, reproducibility, and approximate noise behavior without requiring random values to match a brittle exact sequence unless the seed and generator are fixed.

**Milestone:** truth and noisy measurements are saved separately and can be inspected.

### Days 16–20: state estimation

First explain the estimator’s inputs, outputs, state-transition model, measurement model, and uncertainty in ordinary terms. Then implement a linear Kalman filter for the chosen simple model. Keep matrix operations explicit and testable; a small vetted linear-algebra library may be used if it reduces risk, but document the dependency and the math. Validate on a noise-free case, then on noisy data. Ensure the estimator consumes measurements, not truth.

**Milestone:** estimates track the simulated state and generally improve on raw noisy measurements under the selected scenario.

### Days 21–23: analysis and visualization

Write Python tooling to read the output format, validate required columns, calculate position/velocity error and RMSE, and create a plot with truth, measurement, and estimate series. Label axes, units, and legend. Include a simple way to run analysis on a generated output file.

**Milestone:** one command sequence produces a plot and metrics from a simulation run.

### Days 24–26: tests and continuous integration

Organize unit tests around observable behavior, not private implementation details. Include tests for state updates, sensor sampling/noise configuration, estimator prediction/correction, and output generation. Add a CI workflow that configures CMake, builds, and runs tests on a clean runner. Keep CI aligned with the documented local commands.

**Milestone:** a fresh checkout builds and passes automated tests locally and in CI.

### Days 27–28: reproducibility and documentation

Finish the README with the problem, architecture, prerequisites, build/run/test/analyze instructions, sample output or plot, assumptions, limitations, and next steps. Add a container only if the native workflow is already reliable. If added, make its purpose clear and show the exact command to run it.

**Milestone:** another person can understand the design and reproduce the demo without a live explanation.

### Days 29–30: portfolio and interview preparation

Review the project as a hiring manager might: clear repository landing page, clean history, no accidental generated files or secrets, useful screenshot/plot, and accurate claims. Practice a two-minute project explanation, a deeper architecture walkthrough, and a discussion of one bug or tradeoff. Continue applications and follow-ups.

**Milestone:** polished portfolio artifact plus a concise, truthful interview story.

## 7. Testing plan

Test the system in layers:

1. **Model tests:** deterministic state update and integration behavior.
2. **Sensor tests:** sampling schedule, configuration validation, deterministic seed behavior, and plausible noise statistics.
3. **Estimator tests:** prediction in a no-measurement step, correction toward a measurement, covariance/uncertainty remaining valid, and performance on a simple known scenario.
4. **Simulation tests:** correct sequencing and output row counts/timestamps.
5. **End-to-end check:** run a short fixed-seed scenario and confirm output can be parsed by Python and produces finite metrics.

Use tolerances for floating-point calculations. Keep tests quick and deterministic. A statistical test should use a fixed seed and broad, justified bounds rather than a fragile exact expected random sample.

## 8. CI and container guidance

CI should use the same configure/build/test steps as the README. At minimum, run on a Linux environment and report failures clearly. If multiple compilers or operating systems are easy to support, add them after the single-platform path is reliable.

Containerization is for repeatability, not a project requirement in itself. A minimal container can install build tools and Python requirements, build the executable, run the simulation, and run analysis. Do not put secrets in the image. Avoid adding orchestration tools for this small local demo.

## 9. Documentation and communication

The README should answer, in this order:

- What does this project demonstrate?
- What is the high-level data flow?
- What assumptions and units does the model use?
- How do I build, test, run, and analyze it?
- What should I expect the output to look like?
- What are the current limitations?
- What would be the next engineering improvements?

Add a simple architecture diagram and a representative plot. Keep claims measurable and accurate. Explain that it is a small educational simulation; do not imply flight qualification, operational sensor fusion, or high-fidelity orbital modeling.

## 10. Optional extensions, in priority order

Only attempt extensions after the end-to-end baseline works:

1. Two-dimensional motion and independent position measurements.
2. Compare Euler and RK4 where the chosen dynamics make the difference meaningful.
3. Multiple sensors with different sample rates or noise levels.
4. A small experiment runner that compares seeds/noise levels and summarizes RMSE.
5. A second estimator or a simple baseline (for example, raw measurements) for comparison.
6. More formal message/data interfaces to prepare for a future distributed design.
7. Serialization formats or network transport only if a specific role or learning objective warrants them.

Do not add extensions solely to make the project sound more advanced. A small system whose behavior is understood is stronger than a large system the learner cannot explain.

## 11. Job-search and interview goals

Search for junior/associate software, test, simulation, integration, and systems-adjacent roles in the Colorado Springs region. Read each posting carefully: required experience, citizenship, clearance eligibility, and whether clearance is required at application, start, or later are role-specific. Do not claim clearance or qualifications that are not held.

Prepare a resume version that emphasizes fundamentals, project evidence, tools used, and learning outcomes. Tailor the top skills to each real posting. Reach out to alumni, local engineering groups, recruiters, and engineers with a brief, respectful request for insight; do not lead with a generic request for a job.

Be ready to explain:

- Why separate truth, sensor measurements, estimator, and analysis?
- What does the Kalman filter predict and correct?
- How did you make noisy runs reproducible?
- How did you test a randomized component?
- What tradeoff did you make to keep the project achievable?
- What would need to change before this design could be distributed or used in a real system?
- What did you personally implement, and what would you improve next?

For coding interviews, focus on core data structures, problem decomposition, readable C++, debugging, and explaining tradeoffs. Practice a manageable number of problems consistently rather than attempting an unrelated technology survey.

## 12. Teaching approach for the next chat

Continue in small, reviewable steps. Before each implementation step:

1. Explain the problem in plain language.
2. Show where that component sits in the architecture and what data it receives and returns.
3. Explain the key concepts and choices, including what is intentionally out of scope.
4. Offer a small design or pseudocode sketch.
5. Implement one coherent increment and explain how to run or inspect it.
6. Ask the learner to explain the idea back or predict behavior when that would reveal understanding.

Define new terms when they first appear. Use concrete examples and build from beginner to advanced. Avoid overwhelming the learner with a large code dump. When suggesting a feature, connect it to a project milestone or an actual role requirement. If time is short, prioritize a complete, understandable end-to-end demo and active job applications over optional sophistication.

## 13. Suggested opening for the next chat

“We’re continuing a 30-day job sprint for junior software, test, simulation, or systems-adjacent roles in the Colorado Springs aerospace/defense ecosystem. The portfolio project is a small C++ sensor and state-estimation simulator, with Python analysis. Please teach from beginner to advanced in plain language. Before coding, explain the architecture and data flow, then help me implement one small step at a time. Keep the first version achievable, help me understand every component, and keep job applications moving alongside the project.”
