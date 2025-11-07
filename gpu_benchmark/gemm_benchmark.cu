#include <cstdio>
#include <cstdlib>
#include <chrono>
#include <vector>
#include <cuda.h>
#include <cuda_runtime.h>

// Simple naive GEMM kernel
__global__ void gemm_naive(const float *A, const float *B, float *C, int M, int K, int N) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;
    if (row < M && col < N) {
        float sum = 0.0f;
        for (int k = 0; k < K; ++k)
            sum += A[row * K + k] * B[k * N + col];
        C[row * N + col] = sum;
    }
}

// Helper to fill matrix with random values
void fill_matrix(std::vector<float> &mat) {
    for (size_t i = 0; i < mat.size(); ++i) mat[i] = static_cast<float>(rand()) / RAND_MAX;
}

int main(int argc, char** argv) {
    // Usage: ./gemm_benchmark M K N iterations
    if (argc < 5) {
        printf("Usage: %s M K N iterations\n", argv[0]);
        return 1;
    }
    int M = atoi(argv[1]);
    int K = atoi(argv[2]);
    int N = atoi(argv[3]);
    int iterations = atoi(argv[4]);

    size_t size_A = (size_t)M * K;
    size_t size_B = (size_t)K * N;
    size_t size_C = (size_t)M * N;

    std::vector<float> h_A(size_A), h_B(size_B), h_C(size_C);
    fill_matrix(h_A);
    fill_matrix(h_B);

    float *d_A = nullptr, *d_B = nullptr, *d_C = nullptr;
    cudaMalloc(&d_A, size_A * sizeof(float));
    cudaMalloc(&d_B, size_B * sizeof(float));
    cudaMalloc(&d_C, size_C * sizeof(float));

    cudaMemcpy(d_A, h_A.data(), size_A * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_B, h_B.data(), size_B * sizeof(float), cudaMemcpyHostToDevice);

    // Choose block dims
    dim3 block(16, 16);
    dim3 grid((N + block.x - 1) / block.x, (M + block.y - 1) / block.y);

    // Warmup
    gemm_naive<<<grid, block>>>(d_A, d_B, d_C, M, K, N);
    cudaDeviceSynchronize();

    // Timing using CUDA events
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    float ms = 0.0f;
    // Run multiple iterations and average
    cudaEventRecord(start);
    for (int it = 0; it < iterations; ++it) {
        gemm_naive<<<grid, block>>>(d_A, d_B, d_C, M, K, N);
    }
    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&ms, start, stop);

    double time_s = (ms / 1000.0);
    // FLOPs for GEMM: 2*M*N*K per multiplication
    double flops = 2.0 * (double)M * (double)N * (double)K * (double)iterations;
    double gflops = (flops / 1e9) / time_s;

    // Compute theoretical occupancy using CUDA API
    int blockSize = block.x * block.y; // threads per block
    int device; cudaGetDevice(&device);
    cudaDeviceProp prop; cudaGetDeviceProperties(&prop, device);
    int maxThreadsPerSM = prop.maxThreadsPerMultiProcessor;
    int numSM = prop.multiProcessorCount;
    // occupancy approximation: active warps / max warps (very rough)
    int maxWarpsPerSM = maxThreadsPerSM / 32;
    int warpsPerBlock = blockSize / 32;
    int activeBlocksPerSM = 0;
    cudaOccupancyMaxActiveBlocksPerMultiprocessor(&activeBlocksPerSM, (void*)gemm_naive, blockSize, 0);
    int activeWarpsPerSM = activeBlocksPerSM * warpsPerBlock;
    double occupancy = (double)activeWarpsPerSM / (double)maxWarpsPerSM;
    if (occupancy > 1.0) occupancy = 1.0;

    // Output a simple JSON-like line that the run script can parse
    // Fields: kernel_name, problem_size, iterations, time_s, gflops, occupancy, block_x, block_y, numSM
    printf("kernel_name=gemm_naive,problem_size=%dx%dx%d,iterations=%d,time_s=%.9f,gflops=%.3f,occupancy=%.3f,block=%dx%d,numSM=%d\n",
           M, K, N, iterations, time_s, gflops, occupancy, block.x, block.y, numSM);

    // Cleanup
    cudaFree(d_A);
    cudaFree(d_B);
    cudaFree(d_C);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);

    return 0;
}
