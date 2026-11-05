#pragma once

namespace sim {

// Hand-written 2-element vector and 2x2 matrix value types (DD-004, NFR-002): no linear-algebra
// dependency, so every line the Kalman filter uses can be read and explained. Only the
// operations the filter needs are provided.

struct Vec2 {
    double v0{0.0};
    double v1{0.0};
};

// Row-major: m01 is row 0, column 1.
struct Mat2 {
    double m00{0.0}, m01{0.0};
    double m10{0.0}, m11{0.0};
};

inline Mat2 identity() {
    return Mat2{1.0, 0.0, 0.0, 1.0};
}

inline Vec2 operator+(const Vec2& a, const Vec2& b) {
    return Vec2{a.v0 + b.v0, a.v1 + b.v1};
}

inline Vec2 operator-(const Vec2& a, const Vec2& b) {
    return Vec2{a.v0 - b.v0, a.v1 - b.v1};
}

inline Vec2 operator*(double s, const Vec2& a) {
    return Vec2{s * a.v0, s * a.v1};
}

inline Mat2 operator+(const Mat2& a, const Mat2& b) {
    return Mat2{a.m00 + b.m00, a.m01 + b.m01, a.m10 + b.m10, a.m11 + b.m11};
}

inline Mat2 operator-(const Mat2& a, const Mat2& b) {
    return Mat2{a.m00 - b.m00, a.m01 - b.m01, a.m10 - b.m10, a.m11 - b.m11};
}

inline Mat2 operator*(double s, const Mat2& a) {
    return Mat2{s * a.m00, s * a.m01, s * a.m10, s * a.m11};
}

// Matrix times matrix: entry (r, c) is row r of `a` dotted with column c of `b`.
inline Mat2 operator*(const Mat2& a, const Mat2& b) {
    return Mat2{a.m00 * b.m00 + a.m01 * b.m10, a.m00 * b.m01 + a.m01 * b.m11,
                a.m10 * b.m00 + a.m11 * b.m10, a.m10 * b.m01 + a.m11 * b.m11};
}

// Matrix times column vector.
inline Vec2 operator*(const Mat2& a, const Vec2& x) {
    return Vec2{a.m00 * x.v0 + a.m01 * x.v1, a.m10 * x.v0 + a.m11 * x.v1};
}

inline Mat2 transpose(const Mat2& a) {
    return Mat2{a.m00, a.m10, a.m01, a.m11};
}

// Column vector times row vector: a 2x2 matrix whose (r, c) entry is a_r * b_c.
inline Mat2 outer(const Vec2& a, const Vec2& b) {
    return Mat2{a.v0 * b.v0, a.v0 * b.v1, a.v1 * b.v0, a.v1 * b.v1};
}

}  // namespace sim
