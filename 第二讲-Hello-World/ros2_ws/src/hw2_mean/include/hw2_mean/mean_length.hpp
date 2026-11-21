#ifndef HW2_MEAN_LENGTH_HPP
#define HW2_MEAN_LENGTH_HPP

#include <cstddef>
#include <optional>
#include <vector>

// 和 8.1 里一样，从 cpp_basics 复制过来的
std::optional<double> meanLength(const std::vector<double> & lengths);

std::size_t countAtLeast(const std::vector<double> & lengths, double threshold);

#endif
