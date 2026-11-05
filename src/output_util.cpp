#include "simulator/output_util.hpp"

#include <cmath>
#include <filesystem>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <system_error>

namespace sim {

std::string format_double(double value, const char* what) {
    if (!std::isfinite(value)) {
        throw std::runtime_error(std::string("non-finite value in ") + what);
    }
    std::ostringstream os;
    os.imbue(std::locale::classic());
    os.precision(17);
    os << value;
    return os.str();
}

AtomicFile::AtomicFile(const std::string& path)
    : path_(path), tmp_path_(path + ".tmp"), out_(tmp_path_, std::ios::trunc) {
    if (!out_) {
        throw std::runtime_error(path_ + ": cannot open for writing");
    }
}

AtomicFile::~AtomicFile() {
    if (!committed_) {
        out_.close();
        std::error_code ignored;
        std::filesystem::remove(tmp_path_, ignored);
    }
}

void AtomicFile::commit() {
    if (committed_) {
        return;
    }
    out_.flush();
    const bool ok = static_cast<bool>(out_);
    out_.close();
    if (!ok) {
        throw std::runtime_error(path_ + ": write failed");
    }
    std::error_code ec;
    std::filesystem::rename(tmp_path_, path_, ec);  // atomic on POSIX
    if (ec) {
        throw std::runtime_error(path_ + ": " + ec.message());
    }
    committed_ = true;
}

}  // namespace sim
