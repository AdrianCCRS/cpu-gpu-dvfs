# CMakeLists.txt para benchmark_monitor
cmake_minimum_required(VERSION 3.10)
project(benchmark_monitor CXX)

# C++11 mínimo
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Opciones de compilación
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -Wall -Wextra")

# Buscar Google Benchmark
# Primero intenta encontrarlo instalado en el sistema
find_package(benchmark QUIET)

if(NOT benchmark_FOUND)
    # Si no está instalado, busca en el directorio padre (el repo clonado)
    message(STATUS "Google Benchmark no encontrado en el sistema, buscando en repo local...")
    
    # Añadir el directorio padre donde está el repo de Google Benchmark
    set(BENCHMARK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
    
    # Incluir el build de Google Benchmark
    if(EXISTS "${BENCHMARK_ROOT}/build")
        set(benchmark_DIR "${BENCHMARK_ROOT}/build")
        find_package(benchmark REQUIRED PATHS ${benchmark_DIR})
    else()
        message(FATAL_ERROR 
            "Google Benchmark no encontrado. Por favor:\n"
            "1. Compila Google Benchmark primero:\n"
            "   cd ..\n"
            "   mkdir -p build && cd build\n"
            "   cmake .. -DCMAKE_BUILD_TYPE=Release\n"
            "   make -j\n"
            "2. O instálalo en el sistema:\n"
            "   sudo make install\n")
    endif()
endif()

# Archivos fuente
add_executable(benchmark_monitor
    benchmark_monitor.cpp
    system_monitor.cpp
)

# Linkear con Google Benchmark
target_link_libraries(benchmark_monitor
    benchmark::benchmark
    pthread
)

# Incluir headers locales
target_include_directories(benchmark_monitor PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Mensaje de éxito
message(STATUS "Configuración completada. Ejecuta 'make' para compilar.")
