#!/usr/bin/env bash
# run_gpu_benchmark.sh - Compila y ejecuta gemm_benchmark, muestrea nvidia-smi y genera results_gpu.csv

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$ROOT_DIR/build"
BIN="$BUILD_DIR/gemm_benchmark"
OUTPUT_CSV="$ROOT_DIR/results_gpu.csv"

# Create a temporary working directory for transient files so we don't leave artifacts
TMPDIR=$(mktemp -d)
trap 'rm -rf "${TMPDIR}"' EXIT

# SAMPLE_FILE and GBOUT will be created per-benchmark inside TMPDIR and removed
SAMPLE_FILE=""

# Problem sizes (M K N) - puedes ajustar para "stress"
# Default sizes reduced to small/medium so test runs complete quickly; edit to increase stress.
SIZES=("128 128 128" "256 256 256" "512 512 512")
ITERATIONS=100
SAMPLE_MS=100

# Determine nvcc path robustly: respect NVCC env var, PATH, and common install locations
if [ -n "${NVCC-}" ] && [ -x "${NVCC}" ]; then
    echo "Using NVCC from NVCC env: $NVCC"
elif command -v nvcc >/dev/null 2>&1; then
    NVCC=$(command -v nvcc)
    echo "Found nvcc in PATH: $NVCC"
else
    # Check common CUDA installation paths
    for p in /usr/local/cuda/bin/nvcc /usr/local/cuda-*/bin/nvcc /opt/cuda*/bin/nvcc /usr/bin/nvcc; do
        if [ -x "$p" ]; then
            NVCC="$p"
            break
        fi
    done
    if [ -n "${NVCC-}" ] && [ -x "${NVCC}" ]; then
        echo "Found nvcc at common path: $NVCC"
    else
        echo "nvcc not found. Please install the CUDA toolkit or set NVCC=/path/to/nvcc"
        echo "Common locations: /usr/local/cuda/bin/nvcc or /usr/local/cuda-<version>/bin/nvcc"
        exit 1
    fi
fi

# Build
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
# Pass the detected NVCC to CMake to avoid compiler-not-found issues in some environments
cmake .. -DCMAKE_CUDA_COMPILER="${NVCC}"
make -j 2

# Header CSV (GPU-focused; NO CPU columns)
cat > "$OUTPUT_CSV" <<EOF
timestamp,kernel_name,problem_size,iterations,gpu_core_clock_MHz,gpu_mem_clock_MHz,gpu_utilization_pct,occupancy,throughput_gflops,bandwidth_gbps,power_avg_w,energy_j,edp,gflops_per_watt,gpu_temp_c,ed2p
EOF

# Helper: parse NVML monitor output file (key=value lines)
declare -A SAMPLE_STATS
parse_nvml_output() {
    SAMPLE_STATS[power_avg]=0
    SAMPLE_STATS[util_avg]=0
    SAMPLE_STATS[core_clock_avg]=0
    SAMPLE_STATS[mem_clock_avg]=0
    SAMPLE_STATS[temp_avg]=0
    SAMPLE_STATS[count]=0
    SAMPLE_STATS[duration_s]=0
    SAMPLE_STATS[energy_j]=0

    if [ ! -s "$SAMPLE_FILE" ]; then
        return
    fi

    while IFS='=' read -r key val; do
        case "$key" in
            power_avg_w) SAMPLE_STATS[power_avg]="$val";;
            gpu_utilization_pct) SAMPLE_STATS[util_avg]="$val";;
            gpu_core_clock_MHz) SAMPLE_STATS[core_clock_avg]="$val";;
            gpu_mem_clock_MHz) SAMPLE_STATS[mem_clock_avg]="$val";;
            gpu_temp_c) SAMPLE_STATS[temp_avg]="$val";;
            samples) SAMPLE_STATS[count]="$val";;
            duration_s) SAMPLE_STATS[duration_s]="$val";;
            energy_j) SAMPLE_STATS[energy_j]="$val";;
        esac
    done < "$SAMPLE_FILE"
}

# Helper: read CPU freq (MHz) - best effort
# (No CPU helpers — CSV is GPU-only)

# Main loop over sizes
for s in "${SIZES[@]}"; do
    read -r M K N <<< "$s"
    timestamp=$(date -Iseconds)
    echo "Running GEMM size ${M}x${K}x${N} (iterations=${ITERATIONS})"

    # Use NVML monitor which will launch the benchmark and sample while it runs
    MONITOR_BIN="$BUILD_DIR/gpu_monitor_nvml"
    if [ ! -x "$MONITOR_BIN" ]; then
        echo "gpu_monitor_nvml not found; please build the project so the NVML monitor is available"
        exit 1
    fi
    # Create per-run temp files
    SAMPLE_FILE=$(mktemp "$TMPDIR/sample.XXXX")
    GBOUT=$(mktemp "$TMPDIR/gbout.XXXX.json")

    GBIN="$BUILD_DIR/gemm_benchmark_google"

    if [ -x "$GBIN" ]; then
        echo "Running Google Benchmark under NVML monitor: $GBIN"
        # monitor will write $SAMPLE_FILE; capture GB JSON to GBOUT
        "$MONITOR_BIN" "$SAMPLE_MS" "$SAMPLE_FILE" "$GBIN" --benchmark_repetitions=3 --benchmark_format=json > "$GBOUT" 2>&1 || true
    else
        echo "Running simple binary under NVML monitor: $BIN"
        "$MONITOR_BIN" "$SAMPLE_MS" "$SAMPLE_FILE" "$BIN" "$M" "$K" "$N" "$ITERATIONS" > /dev/null 2>&1 || true
    fi

    # Parse NVML monitor output (from SAMPLE_FILE)
    parse_nvml_output

    # Parse gemm output or Google Benchmark JSON (if present)
    # Set sane defaults so 'set -u' doesn't fail on missing values
    kernel_name="gemm_naive"
    problem_size="${M}x${K}x${N}"
    time_s=0
    gflops=0
    occupancy=0
    bytes_moved=$(( (M*K + K*N + M*N) * 4 ))
    if [ -s "$GBOUT" ]; then
        parsed=$(python3 - <<PY
import json
f = open('$GBOUT')
data = json.load(f)
for b in data.get('benchmarks', []):
    if b.get('run_type') == 'aggregate' and b.get('aggregate_name') == 'mean':
        name = b.get('run_name')
        parts = name.split('/')
        if len(parts) >= 4:
            ps = parts[1] + 'x' + parts[2] + 'x' + parts[3]
        else:
            ps = 'unknown'
        if ps == '%s':
            time_ms = float(b.get('real_time', 0.0))
            counters = b.get('counters', {}) or {}
            gflops = counters.get('gflops', None)
            occupancy = counters.get('occupancy', None)
            bytes_moved = counters.get('bytes', None)
            print(time_ms, gflops if gflops is not None else 'N/A', occupancy if occupancy is not None else 'N/A', bytes_moved if bytes_moved is not None else 'N/A')
            break
PY
)
        if [ -n "$parsed" ]; then
            # parsed: time_ms gflops occupancy bytes
            time_ms=$(echo "$parsed" | awk '{print $1}')
            gflops=$(echo "$parsed" | awk '{print $2}')
            occupancy=$(echo "$parsed" | awk '{print $3}')
            bytes_moved=$(echo "$parsed" | awk '{print $4}')
            if [ "$gflops" = "N/A" ]; then gflops=0; fi
            if [ "$occupancy" = "N/A" ]; then occupancy=0; fi
            if [ "$bytes_moved" = "N/A" ] || [ -z "$bytes_moved" ]; then bytes_moved=$(( (M*K + K*N + M*N) * 4 )); fi
            time_s=$(awk -v t="$time_ms" 'BEGIN{printf("%.6f", t/1000.0)}')
        fi
    fi

    # Compute bandwidth estimate (bytes moved: A + B + C)
    bytes=$(( (M*K + K*N + M*N) * 4 ))
    # bandwidth in Gbps: (bytes / time_s) * 8 / 1e9
    if [ "$time_s" == "" ] || (( $(echo "$time_s <= 0" | bc -l) )); then
        bandwidth_gbps=0
    else
        bandwidth_gbps=$(awk -v b=$bytes -v t=$time_s 'BEGIN{printf("%.3f", (b / t) * 8.0 / 1e9)}')
    fi

    # energy and power
    power_avg_w=${SAMPLE_STATS[power_avg]:-0}
    energy_j=$(awk -v p=$power_avg_w -v t=$time_s 'BEGIN{printf("%.6f", p * t)}')
    edp=$(awk -v e=$energy_j -v t=$time_s 'BEGIN{printf("%.6e", e * t)}')
    gflops_per_watt=$(awk -v g=$gflops -v p=$power_avg_w 'BEGIN{ if(p>0) printf("%.3f", g / p); else print "0" }')
    ed2p=$(awk -v e=$energy_j -v t=$time_s 'BEGIN{printf("%.6e", e * t * t)}')

    threads_used="N/A"

    gpu_util=${SAMPLE_STATS[util_avg]:-0}
    gpu_core_clock=${SAMPLE_STATS[core_clock_avg]:-0}
    gpu_mem_clock=${SAMPLE_STATS[mem_clock_avg]:-0}
    gpu_temp=${SAMPLE_STATS[temp_avg]:-0}

    # Append to CSV (GPU-only columns)
    echo "$timestamp,$kernel_name,$problem_size,$ITERATIONS,$gpu_core_clock,$gpu_mem_clock,$gpu_util,$occupancy,$gflops,$bandwidth_gbps,$power_avg_w,$energy_j,$edp,$gflops_per_watt,$gpu_temp,$ed2p" >> "$OUTPUT_CSV"

    # Clean per-run temp files
    rm -f "$SAMPLE_FILE" "$GBOUT" || true

    echo "Result appended to $OUTPUT_CSV"
    echo ""
done

echo "All done. CSV: $OUTPUT_CSV"
