#include "hw2_mean/mean_length.hpp"

std::optional<double> meanLength(const std::vector<double> & lengths)
{
    if (lengths.empty())
    {
        return std::nullopt;
    }

    double sum = 0.0;
    for (std::size_t i = 0; i < lengths.size(); i++)
    {
        sum = sum + lengths[i];
    }
    return sum / static_cast<double>(lengths.size());
}

std::size_t countAtLeast(const std::vector<double> & lengths, double threshold)
{
    std::size_t count = 0;
    for (std::size_t i = 0; i < lengths.size(); i++)
    {
        if (lengths[i] >= threshold)
        {
            count = count + 1;
        }
    }
    return count;
}
