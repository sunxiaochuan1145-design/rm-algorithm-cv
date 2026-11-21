#include "cpp_basics/mean_length.hpp"

std::size_t countAtLeast(const std::vector<double> & lengths, double threshold)
{
    std::size_t count = 0;
    for (std::size_t i = 0; i < lengths.size(); i++)
    {
        // 题目说"不小于"，所以等于阈值的也要算，这里用 >=
        // 一开始写的 > ，结果测试里"恰好等于阈值"那条没过
        if (lengths[i] >= threshold)
        {
            count = count + 1;
        }
    }
    return count;
}
