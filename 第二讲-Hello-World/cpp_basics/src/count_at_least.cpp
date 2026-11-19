#include "cpp_basics/mean_length.hpp"

std::size_t countAtLeast(const std::vector<double> & lengths, double threshold)
{
  std::size_t count = 0;
  for (double length_px : lengths) {
    if (length_px >= threshold) {
      // 恰好等于阈值也算“不小于”，所以用 >= 而不是 >
      ++count;
    }
  }
  return count;
}
