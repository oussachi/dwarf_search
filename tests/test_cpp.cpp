/*
 * test_cpp.cpp
 * A C++ program that exercises classes, templates, and exception handling
 * so the compiler emits a rich .eh_frame with many FDEs.
 */
#include <iostream>
#include <vector>
#include <stdexcept>
#include <algorithm>
#include <numeric>
#include <string>

/* ---------- template utility ---------- */

template <typename T>
T clamp(T val, T lo, T hi) {
    if (val < lo) return lo;
    if (val > hi) return hi;
    return val;
}

template <typename T>
double mean(const std::vector<T> &v) {
    if (v.empty()) throw std::invalid_argument("mean of empty vector");
    return static_cast<double>(std::accumulate(v.begin(), v.end(), T{}))
           / static_cast<double>(v.size());
}

/* ---------- class with several methods ---------- */

class Matrix {
public:
    Matrix(int rows, int cols)
        : rows_(rows), cols_(cols), data_(rows * cols, 0.0) {}

    void set(int r, int c, double val) {
        data_[r * cols_ + c] = val;
    }

    double get(int r, int c) const {
        return data_[r * cols_ + c];
    }

    Matrix operator+(const Matrix &other) const {
        if (rows_ != other.rows_ || cols_ != other.cols_)
            throw std::invalid_argument("Matrix size mismatch");
        Matrix result(rows_, cols_);
        for (int i = 0; i < rows_ * cols_; i++)
            result.data_[i] = data_[i] + other.data_[i];
        return result;
    }

    void print() const {
        for (int r = 0; r < rows_; r++) {
            for (int c = 0; c < cols_; c++)
                std::cout << get(r, c) << " ";
            std::cout << "\n";
        }
    }

    int rows() const { return rows_; }
    int cols() const { return cols_; }

private:
    int rows_, cols_;
    std::vector<double> data_;
};

/* ---------- free functions ---------- */

static std::string repeat(const std::string &s, int n) {
    std::string out;
    out.reserve(s.size() * n);
    for (int i = 0; i < n; i++) out += s;
    return out;
}

static std::vector<int> sieve(int limit) {
    std::vector<bool> composite(limit + 1, false);
    std::vector<int>  primes;
    for (int i = 2; i <= limit; i++) {
        if (!composite[i]) {
            primes.push_back(i);
            for (int j = 2 * i; j <= limit; j += i)
                composite[j] = true;
        }
    }
    return primes;
}

static void demonstrate_exceptions() {
    try {
        std::vector<int> empty;
        (void)mean(empty);
    } catch (const std::invalid_argument &e) {
        std::cout << "Caught expected exception: " << e.what() << "\n";
    }
}

/* ---------- main ---------- */

int main() {
    /* template functions */
    std::cout << "clamp(15, 0, 10) = " << clamp(15, 0, 10) << "\n";
    std::vector<int> v = {1, 2, 3, 4, 5};
    std::cout << "mean({1..5})     = " << mean(v) << "\n";

    /* matrix */
    Matrix a(2, 2), b(2, 2);
    a.set(0,0,1); a.set(0,1,2); a.set(1,0,3); a.set(1,1,4);
    b.set(0,0,5); b.set(0,1,6); b.set(1,0,7); b.set(1,1,8);
    std::cout << "A + B =\n";
    (a + b).print();

    /* string */
    std::cout << "repeat(\"ab\",3)  = " << repeat("ab", 3) << "\n";

    /* sieve */
    auto primes = sieve(30);
    std::cout << "primes <= 30    = ";
    for (int p : primes) std::cout << p << " ";
    std::cout << "\n";

    /* exceptions */
    demonstrate_exceptions();

    return 0;
}
