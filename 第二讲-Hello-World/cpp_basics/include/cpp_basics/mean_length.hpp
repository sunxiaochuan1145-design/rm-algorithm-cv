#pragma once

#include <cstddef>
#include <optional>
#include <vector>

// 一组灯条长度（单位：像素）的均值。
// 数组为空时没有结果，返回 std::nullopt —— 不是 0，也不是 nan。
std::optional<double> meanLength(const std::vector<double> & lengths);

// 统计不小于阈值 threshold 的个数（“不小于”＝大于等于，边界要算进去）。
std::size_t countAtLeast(const std::vector<double> & lengths, double threshold);
