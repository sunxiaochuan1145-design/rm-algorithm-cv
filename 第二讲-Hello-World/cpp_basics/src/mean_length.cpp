#include "cpp_basics/mean_length.hpp"

std::optional<double> meanLength(const std::vector<double> & lengths)
{
    if (lengths.empty())
    {
        // 一个数都没有，算不了平均值
        return std::nullopt;
    }

    double sum = 0.0;
    for (std::size_t i = 0; i < lengths.size(); i++)
    {
        sum = sum + lengths[i];
    }

    // size() 是整数，先转成 double 再除，不然小数会丢
    return sum / static_cast<double>(lengths.size());
}
