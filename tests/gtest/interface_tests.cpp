#include <gtest/gtest.h>

#include <type_traits>
#include <utility>

#include "simulator/estimator.hpp"
#include "simulator/state.hpp"

namespace {

// True if `E::update(Arg)` compiles.
template <typename E, typename Arg, typename = void>
struct CanUpdateWith : std::false_type {};
template <typename E, typename Arg>
struct CanUpdateWith<E, Arg,
                     std::void_t<decltype(std::declval<E&>().update(std::declval<Arg>()))>>
    : std::true_type {};

}  // namespace

// EST-002 / SYS-002: this is decided at compile time. If someone ever adds an overload that
// accepts the truth, the test binary stops compiling.
static_assert(CanUpdateWith<sim::IEstimator, sim::Measurement>::value,
              "the estimator must accept measurements");
static_assert(!CanUpdateWith<sim::IEstimator, sim::TrueState>::value,
              "the estimator must NOT accept the true state");

// SIM-001: the truth type exists and carries time, position and velocity, with the unit in each
// field name. Assigning to the named fields and reading the types checks both at compile time.
static_assert(std::is_same<decltype(sim::TrueState::t_s), double>::value, "t_s is a double");
static_assert(std::is_same<decltype(sim::TrueState::position_m), double>::value, "position_m");
static_assert(std::is_same<decltype(sim::TrueState::velocity_mps), double>::value, "velocity_mps");

TEST(Interfaces, TrueStateHoldsTimePositionAndVelocity) {
    RecordProperty("requirements", "SIM-001");
    const sim::TrueState s{1.5, 2.5, 3.5};
    EXPECT_EQ(s.t_s, 1.5);
    EXPECT_EQ(s.position_m, 2.5);
    EXPECT_EQ(s.velocity_mps, 3.5);
}

TEST(Interfaces, EstimatorCannotAcceptTruth) {
    RecordProperty("requirements", "EST-002,SYS-002");
    SUCCEED();  // the checks above ran at compile time; this registers the requirement tag
}
