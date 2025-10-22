/*
 * Simple dot product benchmark for CPU DVFS experiments
 * Proyecto 10 - DVFS + ML
 * 
 * Compile: gcc -O2 -o dot dot.c -lm
 * Run: ./dot <vector_size>
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/time.h>

double get_time() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}

double dot_product(double *a, double *b, size_t n) {
    double sum = 0.0;
    for (size_t i = 0; i < n; i++) {
        sum += a[i] * b[i];
    }
    return sum;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <vector_size>\n", argv[0]);
        return 1;
    }
    
    size_t n = atoll(argv[1]);
    printf("Dot product benchmark: vector size = %zu\n", n);
    
    // Allocate vectors
    double *a = (double *)malloc(n * sizeof(double));
    double *b = (double *)malloc(n * sizeof(double));
    
    if (!a || !b) {
        fprintf(stderr, "Memory allocation failed\n");
        return 1;
    }
    
    // Initialize with random values
    srand(42);
    for (size_t i = 0; i < n; i++) {
        a[i] = (double)rand() / RAND_MAX;
        b[i] = (double)rand() / RAND_MAX;
    }
    
    // Warm-up
    volatile double result = dot_product(a, b, n);
    
    // Benchmark
    double start = get_time();
    result = dot_product(a, b, n);
    double end = get_time();
    
    double elapsed = end - start;
    double gflops = (2.0 * n) / (elapsed * 1e9);
    
    printf("Result: %.6f\n", result);
    printf("Time: %.6f seconds\n", elapsed);
    printf("Performance: %.3f GFLOP/s\n", gflops);
    
    free(a);
    free(b);
    
    return 0;
}
