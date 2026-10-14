#pragma once

#include <iosfwd>
#include <string>
#include <vector>

namespace sim {

// Exit codes (IF-02).
inline constexpr int kExitOk = 0;
inline constexpr int kExitRuntimeError = 1;  // runtime or I/O failure; no CSV left behind
inline constexpr int kExitUsageError = 2;    // bad flag or setting; nothing written

// The whole command-line program, parameterized on streams so tests can call it directly.
// main() makes exactly one call to this (TST-001). Errors print as
// `sim: error: <parameter>: <reason>` on `err` (CFG-002).
int cli_main(const std::vector<std::string>& args, std::ostream& out, std::ostream& err);

}  // namespace sim
