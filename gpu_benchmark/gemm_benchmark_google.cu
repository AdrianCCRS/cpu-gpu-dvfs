// Google Benchmark-driven GEMM implemented in a CUDA compilation unit
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <cuda_runtime.h>
#include <benchmark/benchmark.h>

// naive GEMM kernel
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

static void BM_GEMM(benchmark::State& state) {
    const int M = static_cast<int>(state.range(0));
    const int K = static_cast<int>(state.range(1));
    const int N = static_cast<int>(state.range(2));

    size_t size_A = (size_t)M * K;
    size_t size_B = (size_t)K * N;
    size_t size_C = (size_t)M * N;

    std::vector<float> h_A(size_A), h_B(size_B), h_C(size_C);
    for (size_t i = 0; i < size_A; ++i) h_A[i] = static_cast<float>(rand()) / RAND_MAX;
    for (size_t i = 0; i < size_B; ++i) h_B[i] = static_cast<float>(rand()) / RAND_MAX;

    float *d_A=nullptr, *d_B=nullptr, *d_C=nullptr;
    cudaMalloc(&d_A, size_A * sizeof(float));
    cudaMalloc(&d_B, size_B * sizeof(float));
    cudaMalloc(&d_C, size_C * sizeof(float));
    cudaMemcpy(d_A, h_A.data(), size_A * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_B, h_B.data(), size_B * sizeof(float), cudaMemcpyHostToDevice);

    dim3 block(16,16);
    dim3 grid((N + block.x - 1) / block.x, (M + block.y - 1) / block.y);

    // create events
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    // warmup
    gemm_naive<<<grid, block>>>(d_A,d_B,d_C,M,K,N);
    cudaDeviceSynchronize();

    // Compute occupancy approximation and set as a counter
    int device; cudaGetDevice(&device);
    cudaDeviceProp prop; cudaGetDeviceProperties(&prop, device);
    int maxThreadsPerSM = prop.maxThreadsPerMultiProcessor;
    int numSM = prop.multiProcessorCount;
    int maxWarpsPerSM = maxThreadsPerSM / 32;
    int blockSize = block.x * block.y;
    int warpsPerBlock = blockSize / 32;
    int activeBlocksPerSM = 0;
    cudaOccupancyMaxActiveBlocksPerMultiprocessor(&activeBlocksPerSM, (void*)gemm_naive, blockSize, 0);
    int activeWarpsPerSM = activeBlocksPerSM * warpsPerBlock;
    double occupancy = maxWarpsPerSM>0 ? (double)activeWarpsPerSM / (double)maxWarpsPerSM : 0.0;
    if (occupancy > 1.0) occupancy = 1.0;

    // Use manual timing so Google Benchmark controls iterations
    for (auto _ : state) {
        // record GPU time
        cudaEventRecord(start);
        gemm_naive<<<grid, block>>>(d_A,d_B,d_C,M,K,N);
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms=0.0f;
        cudaEventElapsedTime(&ms, start, stop);
        double seconds = ms / 1000.0;
        // Report the time for this iteration to Google Benchmark (manual time)
        state.SetIterationTime(seconds);
        // Set items processed (useful for throughput reporting)
        double flops = 2.0 * (double)M * (double)N * (double)K;
        state.SetItemsProcessed(static_cast<long long>(flops));
        // report counters to Google Benchmark JSON
        double gflops = (flops / 1e9) / seconds;
        state.counters["gflops"] = gflops;
        state.counters["occupancy"] = occupancy;
        state.counters["bytes"] = static_cast<double>((M*K + K*N + M*N) * 4);
    }

    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    cudaFree(d_A);
    cudaFree(d_B);
    cudaFree(d_C);
}

// Register benchmarks for several sizes
BENCHMARK(BM_GEMM)->Args({128,128,128})->UseManualTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_GEMM)->Args({256,256,256})->UseManualTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_GEMM)->Args({512,512,512})->UseManualTime()->Unit(benchmark::kMillisecond);

BENCHMARK_MAIN();
