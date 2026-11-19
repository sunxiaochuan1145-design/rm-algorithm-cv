#include "cpp_basics/mean_length.hpp"

std::optional<double> meanLength(const std::vector<double> & lengths)
{
  if (lengths.empty()) {
    // 0 个数的均值没有定义：不能返回 0，也不该返回 nan
    return std::nullopt;
  }

  double sum = 0.0;
  for (double length_px : lengths) {
    sum += length_px;
  }
  // 先转成 double 再相除，避免整数除法把小数部分丢掉
  return sum / static_cast<double>(lengths.size());
}
