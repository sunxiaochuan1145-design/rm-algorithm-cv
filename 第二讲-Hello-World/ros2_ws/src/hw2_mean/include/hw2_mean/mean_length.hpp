#pragma once

#include <cstddef>
#include <optional>
#include <vector>

// 8.1 的算法原样复用：声明在这里，定义在 src/mean_length.cpp。
std::optional<double> meanLength(const std::vector<double> & lengths);

// 统计不小于阈值的个数（8.2 的两个节点用不到，但复制过来一起编进库里）。
std::size_t countAtLeast(const std::vector<double> & lengths, double threshold);
