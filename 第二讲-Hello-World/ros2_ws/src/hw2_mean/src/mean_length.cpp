#include "hw2_mean/mean_length.hpp"

std::optional<double> meanLength(const std::vector<double> & lengths)
{
  if (lengths.empty()) {
    return std::nullopt;
  }

  double sum = 0.0;
  for (double length_px : lengths) {
    sum += length_px;
  }
  return sum / static_cast<double>(lengths.size());
}
