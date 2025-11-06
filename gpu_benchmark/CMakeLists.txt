cmake_minimum_required(VERSION 3.10)
project(gpu_gemm_benchmark LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CUDA_STANDARD 14)

add_executable(gemm_benchmark gemm_benchmark.cu)

# Optional: build Google Benchmark-driven binary if Google Benchmark is available
find_package(benchmark QUIET)
if(benchmark_FOUND)
	message(STATUS "Found Google Benchmark: building gemm_benchmark_google")
		add_executable(gemm_benchmark_google gemm_benchmark_google.cu)
	target_link_libraries(gemm_benchmark_google PRIVATE benchmark::benchmark)
	set_target_properties(gemm_benchmark_google PROPERTIES
		CUDA_SEPARABLE_COMPILATION ON)
else()
	message(STATUS "Google Benchmark not found: skipping gemm_benchmark_google")
endif()

# NVML-based GPU monitor utility (only build if NVML headers/libs are available)
include(CheckIncludeFileCXX)

# Look for nvml.h in common CUDA/include locations as well as system include paths
find_path(NVML_INCLUDE_DIR nvml.h
	PATHS
		/usr/include
		/usr/local/include
		/usr/local/cuda/include
		/usr/local/cuda-*/include
		/usr/include/nvidia
		$ENV{CUDA_HOME}/include
		$ENV{CUDA_PATH}/include
	NO_DEFAULT_PATH
)

if(NVML_INCLUDE_DIR)
	message(STATUS "Found NVML headers in: ${NVML_INCLUDE_DIR}")
	include_directories(${NVML_INCLUDE_DIR})
	add_executable(gpu_monitor_nvml gpu_monitor_nvml.cpp)
	# Try to find the NVML library in standard locations
	find_library(NVML_LIB nvidia-ml
		PATHS
			/usr/lib
			/usr/lib64
			/usr/local/cuda/lib64
			/usr/local/cuda/lib
			/usr/lib/nvidia
			/usr/lib/x86_64-linux-gnu
		NO_DEFAULT_PATH
	)
	if(NVML_LIB)
		message(STATUS "Found NVML library: ${NVML_LIB}")
		target_link_libraries(gpu_monitor_nvml PRIVATE ${NVML_LIB})
	else()
		message(WARNING "NVML library not found; gpu_monitor_nvml target created but not linked to nvidia-ml. You may need to set linker paths.")
	endif()
else()
	# Fallback: try to detect nvml.h via check_include_file_cxx (system include paths)
	check_include_file_cxx("nvml.h" HAVE_NVML_H)
	if(HAVE_NVML_H)
		message(STATUS "Found NVML headers via system include path")
		add_executable(gpu_monitor_nvml gpu_monitor_nvml.cpp)
		find_library(NVML_LIB nvidia-ml)
		if(NVML_LIB)
			target_link_libraries(gpu_monitor_nvml PRIVATE ${NVML_LIB})
		endif()
	else()
		message(WARNING "NVML headers not found (nvml.h). Skipping build of gpu_monitor_nvml.")
	endif()
endif()

# Use fast math optionally
# target_compile_options(gemm_benchmark PRIVATE $<$<COMPILE_LANGUAGE:CUDA>:--use_fast_math>)

# Link flags if needed
# target_link_libraries(gemm_benchmark PRIVATE nvidia-ml)
