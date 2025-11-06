#!/bin/bash
# check_metrics_availability.sh - Verifica disponibilidad de métricas en el sistema

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║           🔍 VERIFICACIÓN DE DISPONIBILIDAD DE MÉTRICAS                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ============================================================
# 1. CPUFreq - Frecuencia y Governor
# ============================================================
echo "1️⃣  CPUFreq - Frecuencia y Governor"
echo "────────────────────────────────────────────────────────────────────────────"

FREQ_FILE="/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
GOV_FILE="/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"

if [ -f "$FREQ_FILE" ]; then
    freq=$(cat "$FREQ_FILE" 2>/dev/null)
    freq_mhz=$(echo "scale=2; $freq / 1000" | bc)
    echo -e "${GREEN}✅ Frecuencia disponible${NC}"
    echo "   Ubicación: $FREQ_FILE"
    echo "   Valor actual: ${freq_mhz} MHz"
else
    echo -e "${RED}❌ Frecuencia NO disponible${NC}"
    echo "   Archivo no existe: $FREQ_FILE"
fi

if [ -f "$GOV_FILE" ]; then
    governor=$(cat "$GOV_FILE" 2>/dev/null)
    echo -e "${GREEN}✅ Governor disponible${NC}"
    echo "   Ubicación: $GOV_FILE"
    echo "   Valor actual: $governor"
else
    echo -e "${RED}❌ Governor NO disponible${NC}"
fi

echo ""

# ============================================================
# 2. RAPL - Energía
# ============================================================
echo "2️⃣  RAPL - Energía (Intel)"
echo "────────────────────────────────────────────────────────────────────────────"

RAPL_BASE="/sys/class/powercap/intel-rapl"

if [ -d "$RAPL_BASE" ]; then
    echo -e "${GREEN}✅ RAPL disponible${NC}"
    echo "   Ubicación: $RAPL_BASE"
    
    # Buscar dominios RAPL
    rapl_domains=$(find "$RAPL_BASE" -name "energy_uj" 2>/dev/null)
    
    if [ ! -z "$rapl_domains" ]; then
        echo "   Dominios encontrados:"
        for domain in $rapl_domains; do
            domain_name=$(dirname "$domain")
            domain_name=$(basename "$domain_name")
            
            # Intentar leer energía
            if [ "$EUID" -eq 0 ]; then
                energy=$(cat "$domain" 2>/dev/null || echo "Error de lectura")
                echo "     - $domain_name: $energy µJ"
            else
                echo "     - $domain_name: (requiere sudo para leer)"
            fi
        done
        
        if [ "$EUID" -ne 0 ]; then
            echo -e "   ${YELLOW}⚠️  Ejecuta con sudo para leer valores${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  No se encontraron dominios RAPL${NC}"
    fi
else
    echo -e "${RED}❌ RAPL NO disponible${NC}"
    echo "   Posibles razones:"
    echo "   - CPU no es Intel"
    echo "   - RAPL deshabilitado en BIOS"
    echo "   - Sistema virtualizado"
fi

echo ""

# ============================================================
# 3. Temperatura
# ============================================================
echo "3️⃣  Temperatura"
echo "────────────────────────────────────────────────────────────────────────────"

found_temp=false

# Thermal zones
for zone in /sys/class/thermal/thermal_zone*/temp; do
    if [ -f "$zone" ]; then
        temp=$(cat "$zone" 2>/dev/null)
        temp_c=$(echo "scale=1; $temp / 1000" | bc)
        zone_name=$(basename $(dirname "$zone"))
        echo -e "${GREEN}✅ Temperatura disponible${NC}"
        echo "   Ubicación: $zone"
        echo "   Zona: $zone_name"
        echo "   Valor actual: ${temp_c} °C"
        found_temp=true
        break
    fi
done

# HWMon (alternativo)
if [ "$found_temp" = false ]; then
    for hwmon in /sys/class/hwmon/hwmon*/temp*_input; do
        if [ -f "$hwmon" ]; then
            temp=$(cat "$hwmon" 2>/dev/null)
            temp_c=$(echo "scale=1; $temp / 1000" | bc)
            echo -e "${GREEN}✅ Temperatura disponible (hwmon)${NC}"
            echo "   Ubicación: $hwmon"
            echo "   Valor actual: ${temp_c} °C"
            found_temp=true
            break
        fi
    done
fi

if [ "$found_temp" = false ]; then
    echo -e "${RED}❌ Temperatura NO disponible${NC}"
fi

echo ""

# ============================================================
# 4. perf - Contadores de rendimiento
# ============================================================
echo "4️⃣  perf - Contadores de rendimiento"
echo "────────────────────────────────────────────────────────────────────────────"

if command -v perf &> /dev/null; then
    perf_version=$(perf --version 2>&1)
    echo -e "${GREEN}✅ perf disponible${NC}"
    echo "   Versión: $perf_version"
    
    # Verificar eventos disponibles
    echo "   Eventos hardware disponibles:"
    
    for event in instructions cycles cache-misses branch-misses; do
        if perf list 2>&1 | grep -q "$event"; then
            echo -e "     ${GREEN}✅${NC} $event"
        else
            echo -e "     ${RED}❌${NC} $event"
        fi
    done
    
    # Verificar permisos
    if [ "$EUID" -ne 0 ]; then
        echo -e "   ${YELLOW}⚠️  Ejecuta con sudo para acceso completo a contadores hardware${NC}"
        
        # Verificar paranoid level
        paranoid_file="/proc/sys/kernel/perf_event_paranoid"
        if [ -f "$paranoid_file" ]; then
            paranoid=$(cat "$paranoid_file")
            echo "   Nivel de paranoid: $paranoid"
            
            case $paranoid in
                -1)
                    echo "     (-1 = sin restricciones)"
                    ;;
                0)
                    echo "     (0 = raw access, kernel profiling permitido)"
                    ;;
                1)
                    echo "     (1 = kernel profiling restringido)"
                    ;;
                2)
                    echo "     (2 = CPU events solo para procesos propios)"
                    ;;
                *)
                    echo "     (nivel restrictivo: $paranoid)"
                    ;;
            esac
            
            if [ "$paranoid" -gt 1 ]; then
                echo -e "   ${YELLOW}💡 Para reducir restricciones (temporal):${NC}"
                echo "      sudo sysctl -w kernel.perf_event_paranoid=1"
            fi
        fi
    fi
else
    echo -e "${RED}❌ perf NO disponible${NC}"
    echo "   Instala con:"
    echo "   - Ubuntu/Debian: sudo apt-get install linux-tools-common linux-tools-generic"
    echo "   - Fedora: sudo dnf install perf"
fi

echo ""

# ============================================================
# 5. Número de CPUs
# ============================================================
echo "5️⃣  Información de CPU"
echo "────────────────────────────────────────────────────────────────────────────"

if command -v nproc &> /dev/null; then
    num_cpus=$(nproc)
    echo -e "${GREEN}✅ Número de CPUs/Cores${NC}"
    echo "   CPUs disponibles: $num_cpus"
fi

if [ -f /proc/cpuinfo ]; then
    cpu_model=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)
    echo "   Modelo: $cpu_model"
fi

echo ""

# ============================================================
# Resumen
# ============================================================
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                              📊 RESUMEN                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Contador de métricas disponibles
available=0
total=5

[ -f "$FREQ_FILE" ] && ((available++))
[ -d "$RAPL_BASE" ] && ((available++))
[ "$found_temp" = true ] && ((available++))
command -v perf &> /dev/null && ((available++))
command -v nproc &> /dev/null && ((available++))

echo "Métricas disponibles: $available / $total"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}💡 TIP: Ejecuta este script con sudo para ver todos los valores:${NC}"
    echo "   sudo ./check_metrics_availability.sh"
    echo ""
fi

echo "Para ejecutar el benchmark con todas las métricas:"
echo "   sudo ./run_benchmark_with_perf.sh"
echo ""
