#!/bin/bash
# build.sh - Script de compilación automática

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║              🔨 COMPILANDO BENCHMARK MONITOR C++                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "CMakeLists.txt" ]; then
    echo -e "${RED}❌ Error: CMakeLists.txt no encontrado${NC}"
    echo "   Ejecuta este script desde el directorio benchmark_monitor_C/"
    exit 1
fi

# Verificar que Google Benchmark está compilado
if [ ! -f "../build/lib/libbenchmark.a" ]; then
    echo -e "${YELLOW}⚠️  Google Benchmark no está compilado${NC}"
    echo ""
    echo "📦 Compilando Google Benchmark primero..."
    
    cd ..
    
    if [ ! -d "build" ]; then
        mkdir build
    fi
    
    cd build
    echo "  → Ejecutando cmake..."
    cmake .. -DCMAKE_BUILD_TYPE=Release -DBENCHMARK_DOWNLOAD_DEPENDENCIES=ON >/dev/null 2>&1 || {
        echo -e "${RED}❌ Error en cmake${NC}"
        exit 1
    }
    
    echo "  → Compilando (esto puede tomar unos minutos)..."
    make -j$(nproc) >/dev/null 2>&1 || {
        echo -e "${RED}❌ Error en make${NC}"
        exit 1
    }
    
    cd ../benchmark_monitor_C
    echo -e "${GREEN}✅ Google Benchmark compilado${NC}"
    echo ""
fi

# Crear directorio de build
if [ ! -d "build" ]; then
    mkdir build
fi

cd build

# Ejecutar cmake
echo "🔧 Configurando proyecto con CMake..."
cmake .. -DCMAKE_BUILD_TYPE=Release || {
    echo -e "${RED}❌ Error en cmake${NC}"
    exit 1
}

# Compilar
echo "🔨 Compilando benchmark_monitor..."
make -j$(nproc) || {
    echo -e "${RED}❌ Error en make${NC}"
    exit 1
}

# Copiar el binario al directorio raíz para facilitar ejecución
cp benchmark_monitor ../ || {
    echo -e "${YELLOW}⚠️  No se pudo copiar el binario${NC}"
}

cd ..

echo ""
echo -e "${GREEN}✅ Compilación exitosa!${NC}"
echo ""
echo "📄 Binario generado: benchmark_monitor"
echo ""
echo "🚀 Para ejecutar:"
echo "   ./benchmark_monitor                    # Ejecución simple"
echo "   sudo ./run_benchmark_with_perf.sh      # Con métricas de perf"
echo ""
