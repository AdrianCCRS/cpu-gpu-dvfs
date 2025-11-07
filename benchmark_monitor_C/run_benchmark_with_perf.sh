#!/bin/bash
# run_benchmark_with_perf.sh - Ejecuta el benchmark con perf stat y combina métricas

set -e

BENCHMARK_BINARY="./benchmark_monitor"
OUTPUT_CSV="results_cpp.csv"
PERF_OUTPUT="perf_output.tmp"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║         🎯 BENCHMARK MONITOR C++ - Con Integración de perf stat             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar permisos
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  Advertencia: No estás ejecutando como root${NC}"
    echo "   Algunas métricas pueden no estar disponibles (RAPL, perf)"
    echo ""
    read -p "¿Continuar de todos modos? (s/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "Abortando..."
        exit 1
    fi
fi

# Verificar que el binario existe
if [ ! -f "$BENCHMARK_BINARY" ]; then
    echo -e "${RED}❌ Error: $BENCHMARK_BINARY no existe${NC}"
    echo "   Compílalo primero con: ./build.sh"
    exit 1
fi

# Verificar que perf está disponible
if ! command -v perf &> /dev/null; then
    echo -e "${YELLOW}⚠️  Advertencia: 'perf' no está disponible${NC}"
    echo "   Ejecutando sin métricas de perf..."
    echo ""
    $BENCHMARK_BINARY "$@"
    exit 0
fi

echo "🚀 Ejecutando benchmark con perf stat..."
echo ""

# Ejecutar con perf stat
perf stat \
    -e instructions,cycles,cache-misses,branch-misses \
    -x ',' \
    -o "$PERF_OUTPUT" \
    $BENCHMARK_BINARY "$@" 2>&1

# Verificar si se generaron resultados
if [ ! -f "$OUTPUT_CSV" ]; then
    echo -e "${RED}❌ Error: No se generó $OUTPUT_CSV${NC}"
    exit 1
fi

# Procesar métricas de perf
if [ -f "$PERF_OUTPUT" ]; then
    echo ""
    echo "📊 Métricas de perf stat:"
    echo "────────────────────────────────────────────────────────────────────────────"
    
    # Parsear métricas de perf (obtener solo el primer valor de cada métrica)
    instructions=$(grep "instructions" "$PERF_OUTPUT" | head -1 | awk -F',' '{print $1}' | tr -d ' ')
    cycles=$(grep -E "cycles[^-]" "$PERF_OUTPUT" | head -1 | awk -F',' '{print $1}' | tr -d ' ')
    cache_misses=$(grep "cache-misses" "$PERF_OUTPUT" | head -1 | awk -F',' '{print $1}' | tr -d ' ')
    branch_misses=$(grep "branch-misses" "$PERF_OUTPUT" | head -1 | awk -F',' '{print $1}' | tr -d ' ')
    
    # Valores por defecto si no se obtuvieron
    instructions=${instructions:-0}
    cycles=${cycles:-0}
    cache_misses=${cache_misses:-0}
    branch_misses=${branch_misses:-0}
    
    # Calcular IPC
    if [ ! -z "$instructions" ] && [ ! -z "$cycles" ] && [ "$cycles" -gt 0 ] 2>/dev/null; then
        ipc=$(echo "scale=3; $instructions / $cycles" | bc 2>/dev/null || echo "0")
        echo "  Instructions:   $instructions"
        echo "  Cycles:         $cycles"
        echo "  IPC:            $ipc"
        echo "  Cache misses:   $cache_misses"
        echo "  Branch misses:  $branch_misses"
        echo ""
        echo "  ℹ️  Nota: Estas son métricas agregadas de TODOS los benchmarks"
        echo "     Para métricas por benchmark individual, se necesitaría modificar"
        echo "     el código C++ para integrar perf directamente."
    else
        ipc=0
        echo "  ⚠️  No se pudieron obtener métricas de perf"
    fi
    
    # Limpiar archivo temporal
    rm -f "$PERF_OUTPUT"
fi

echo ""
echo "✅ Benchmark completado"
echo "📄 Resultados guardados en: $OUTPUT_CSV"
echo ""

# Mostrar primeras líneas del CSV
if [ -f "$OUTPUT_CSV" ]; then
    echo "📊 Primeros resultados:"
    echo "────────────────────────────────────────────────────────────────────────────"
    head -3 "$OUTPUT_CSV" | column -t -s','
    echo ""
fi
