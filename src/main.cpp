#include <iostream>
#include <string>
#include <vector>

#include "simulator/cli.hpp"

int main(int argc, char** argv) {
    return sim::cli_main(std::vector<std::string>(argv + 1, argv + argc), std::cout, std::cerr);
}
