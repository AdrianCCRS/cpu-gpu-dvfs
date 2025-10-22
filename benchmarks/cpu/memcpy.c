/*
 * Simple memcpy benchmark for CPU DVFS experiments
 * Proyecto 10 - DVFS + ML
 * 
 * Compile: gcc -O2 -o memcpy_bench memcpy.c
 * Run: ./memcpy_bench <size_in_bytes>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>

double get_time() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <size_in_bytes>\n", argv[0]);
        return 1;
    }
    
    size_t size = atoll(argv[1]);
    printf("Memcpy benchmark: size = %zu bytes (%.2f MB)\n", 
           size, size / (1024.0 * 1024.0));
    
    // Allocate source and destination buffers
    char *src = (char *)malloc(size);
    char *dst = (char *)malloc(size);
    
    if (!src || !dst) {
        fprintf(stderr, "Memory allocation failed\n");
        return 1;
    }
    
    // Initialize source buffer
    memset(src, 0xAB, size);
    
    // Warm-up
    memcpy(dst, src, size);
    
    // Benchmark
    double start = get_time();
    memcpy(dst, src, size);
    double end = get_time();
    
    double elapsed = end - start;
    double bandwidth_gbps = (size / (1024.0 * 1024.0 * 1024.0)) / elapsed;
    
    printf("Time: %.6f seconds\n", elapsed);
    printf("Bandwidth: %.3f GB/s\n", bandwidth_gbps);
    
    // Verify (simple check)
    int errors = 0;
    for (size_t i = 0; i < size && errors < 10; i++) {
        if (dst[i] != src[i]) {
            fprintf(stderr, "Mismatch at byte %zu\n", i);
            errors++;
        }
    }
    if (errors == 0) {
        printf("Verification: PASSED\n");
    }
    
    free(src);
    free(dst);
    
    return 0;
}
