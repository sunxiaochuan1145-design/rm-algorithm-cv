#ifndef MEAN_LENGTH_HPP
#define MEAN_LENGTH_HPP

#include <cstddef>
#include <optional>
#include <vector>

// 求一组长度的平均值，空数组返回 nullopt
std::optional<double> meanLength(const std::vector<double> & lengths);

// 数一下有多少个长度不小于 threshold
std::size_t countAtLeast(const std::vector<double> & lengths, double threshold);

#endif
