#include <gtest/gtest.h>

#include "simulator/mat2.hpp"

using namespace sim;

// These tests check the hand-written 2x2 maths the Kalman filter is built on (D6, DD-004).
// The expected values were worked out on paper with small integers, so they are exact in
// floating point and the tests compare exactly. They cite NFR-002 because that requirement is
// the one that obliges the project to carry its own matrix code.

namespace {
const Mat2 kA{1.0, 2.0, 3.0, 4.0};
const Mat2 kB{5.0, 6.0, 7.0, 8.0};

void expect_equal(const Mat2& got, const Mat2& want) {
    EXPECT_DOUBLE_EQ(got.m00, want.m00);
    EXPECT_DOUBLE_EQ(got.m01, want.m01);
    EXPECT_DOUBLE_EQ(got.m10, want.m10);
    EXPECT_DOUBLE_EQ(got.m11, want.m11);
}
}  // namespace

TEST(Mat2, MatrixProductByHand) {
    RecordProperty("requirements", "NFR-002");
    // [1 2][5 6]   [1*5+2*7  1*6+2*8]   [19 22]
    // [3 4][7 8] = [3*5+4*7  3*6+4*8] = [43 50]
    expect_equal(kA * kB, Mat2{19.0, 22.0, 43.0, 50.0});
}

TEST(Mat2, ProductIsNotCommutative) {
    RecordProperty("requirements", "NFR-002");
    // Guards against a "transposed" bug that would hide when both orders happen to agree.
    // [5 6][1 2]   [5+18  10+24]   [23 34]
    // [7 8][3 4] = [7+24  14+32] = [31 46]
    expect_equal(kB * kA, Mat2{23.0, 34.0, 31.0, 46.0});
}

TEST(Mat2, IdentityLeavesAMatrixUnchanged) {
    RecordProperty("requirements", "NFR-002");
    expect_equal(identity() * kA, kA);
    expect_equal(kA * identity(), kA);
}

TEST(Mat2, MatrixTimesVector) {
    RecordProperty("requirements", "NFR-002");
    // [1 2][1]   [1*1+2*1]   [3]
    // [3 4][1] = [3*1+4*1] = [7]
    const Vec2 got = kA * Vec2{1.0, 1.0};
    EXPECT_DOUBLE_EQ(got.v0, 3.0);
    EXPECT_DOUBLE_EQ(got.v1, 7.0);
}

TEST(Mat2, TransposeSwapsTheOffDiagonal) {
    RecordProperty("requirements", "NFR-002");
    expect_equal(transpose(kA), Mat2{1.0, 3.0, 2.0, 4.0});
}

TEST(Mat2, SumDifferenceAndScalarMultiple) {
    RecordProperty("requirements", "NFR-002");
    expect_equal(kA + kB, Mat2{6.0, 8.0, 10.0, 12.0});
    expect_equal(kA - kB, Mat2{-4.0, -4.0, -4.0, -4.0});
    expect_equal(2.0 * kA, Mat2{2.0, 4.0, 6.0, 8.0});
}

TEST(Mat2, OuterProductOfColumnAndRow) {
    RecordProperty("requirements", "NFR-002");
    // [1]        [1*3 1*4]   [3 4]
    // [2] [3 4] = [2*3 2*4] = [6 8]
    expect_equal(outer(Vec2{1.0, 2.0}, Vec2{3.0, 4.0}), Mat2{3.0, 4.0, 6.0, 8.0});
}

TEST(Vec2, SumDifferenceAndScalarMultiple) {
    RecordProperty("requirements", "NFR-002");
    const Vec2 a{1.0, 2.0};
    const Vec2 b{10.0, 20.0};
    EXPECT_DOUBLE_EQ((a + b).v1, 22.0);
    EXPECT_DOUBLE_EQ((b - a).v0, 9.0);
    EXPECT_DOUBLE_EQ((3.0 * a).v1, 6.0);
}
