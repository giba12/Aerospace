#pragma once

#include <fstream>
#include <string>

namespace sim {

// A number as text that round-trips any double exactly (17 significant digits, OUT-002), with
// '.' as the decimal separator whatever the locale. Throws std::runtime_error naming `what` if
// the value is not finite, so "nan" and "inf" can never reach a file (OUT-005).
std::string format_double(double value, const char* what);

// A file that appears all at once or not at all (OUT-004, RAII). Writes go to `<path>.tmp`;
// commit() renames it onto `<path>`. If the object is destroyed without commit(), for example
// because an exception unwound the run, the temp file is deleted. Shared by the CSV recorder
// and the sidecar writer.
class AtomicFile {
public:
    explicit AtomicFile(const std::string& path);  // throws std::runtime_error if unwritable
    ~AtomicFile();
    AtomicFile(const AtomicFile&) = delete;
    AtomicFile& operator=(const AtomicFile&) = delete;

    std::ostream& stream() { return out_; }
    void commit();  // idempotent; throws std::runtime_error if the write or rename failed

private:
    std::string path_;
    std::string tmp_path_;
    std::ofstream out_;
    bool committed_{false};
};

}  // namespace sim
