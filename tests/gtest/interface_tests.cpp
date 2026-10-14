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

TEST(Interfaces, EstimatorCannotAcceptTruth) {
    RecordProperty("requirements", "EST-002,SYS-002");
    SUCCEED();  // the checks above ran at compile time; this registers the requirement tag
}
