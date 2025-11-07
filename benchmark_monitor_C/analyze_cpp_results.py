#!/usr/bin/env python3
"""
analyze_cpp_results.py - Analizador de resultados de benchmark_monitor C++
Lee results_cpp.csv y genera análisis estadísticos
"""

import csv
import sys
from pathlib import Path
import statistics

def load_results(filename="results_cpp.csv"):
    """Carga resultados del CSV"""
    if not Path(filename).exists():
        print(f"❌ Error: {filename} no existe")
        print(f"   Ejecuta primero: sudo ./run_benchmark_with_perf.sh")
        sys.exit(1)
    
    results = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convertir valores numéricos
            for key in row:
                if key not in ['timestamp', 'benchmark', 'cpu_governor']:
                    try:
                        row[key] = float(row[key])
                    except (ValueError, TypeError):
                        row[key] = None
            results.append(row)
    
    return results

def analyze_by_benchmark(results):
    """Analiza resultados agrupados por benchmark"""
    
    benchmarks = {}
    for r in results:
        # Extraer nombre base del benchmark (sin el tamaño)
        name = r['benchmark'].split('/')[0] if '/' in r['benchmark'] else r['benchmark']
        if name not in benchmarks:
            benchmarks[name] = []
        benchmarks[name].append(r)
    
    print("\n" + "="*80)
    print("ANÁLISIS POR BENCHMARK".center(80))
    print("="*80 + "\n")
    
    for bench_name, data in sorted(benchmarks.items()):
        print(f"📊 {bench_name}")
        print("-" * 80)
        
        # Estadísticas de tiempo
        times = [r['time_s'] for r in data if r['time_s'] is not None and r['time_s'] > 0]
        if times:
            print(f"   Tiempo:")
            print(f"     - Min:     {min(times)*1000:.3f} ms")
            print(f"     - Max:     {max(times)*1000:.3f} ms")
            print(f"     - Media:   {statistics.mean(times)*1000:.3f} ms")
            print(f"     - Mediana: {statistics.median(times)*1000:.3f} ms")
        
        # Estadísticas de energía
        energies = [r['energy_J'] for r in data if r['energy_J'] is not None and r['energy_J'] > 0]
        if energies:
            print(f"   Energía:")
            print(f"     - Min:   {min(energies):.6f} J")
            print(f"     - Max:   {max(energies):.6f} J")
            print(f"     - Media: {statistics.mean(energies):.6f} J")
        
        # Estadísticas de potencia
        powers = [r['power_avg_W'] for r in data if r['power_avg_W'] is not None and r['power_avg_W'] > 0]
        if powers:
            print(f"   Potencia promedio:")
            print(f"     - Min:   {min(powers):.3f} W")
            print(f"     - Max:   {max(powers):.3f} W")
            print(f"     - Media: {statistics.mean(powers):.3f} W")
        
        # Estadísticas de temperatura
        temps = [r['temperature_C'] for r in data if r['temperature_C'] is not None and r['temperature_C'] > 0]
        if temps:
            print(f"   Temperatura:")
            print(f"     - Min:   {min(temps):.1f} °C")
            print(f"     - Max:   {max(temps):.1f} °C")
            print(f"     - Media: {statistics.mean(temps):.1f} °C")
        
        print()

def analyze_by_size(results):
    """Analiza cómo escalan los benchmarks con el tamaño"""
    
    print("\n" + "="*80)
    print("ANÁLISIS POR TAMAÑO DE DATOS".center(80))
    print("="*80 + "\n")
    
    # Agrupar por tamaño
    sizes = {}
    for r in results:
        N = r['N']
        if N not in sizes:
            sizes[N] = []
        sizes[N].append(r)
    
    for N in sorted(sizes.keys()):
        if N == 0:
            continue
        
        data = sizes[N]
        print(f"📏 N = {N:.1e}")
        print("-" * 80)
        
        # Tiempo promedio por benchmark
        by_bench = {}
        for r in data:
            bench = r['benchmark'].split('/')[0] if '/' in r['benchmark'] else r['benchmark']
            if bench not in by_bench:
                by_bench[bench] = []
            if r['time_s'] is not None and r['time_s'] > 0:
                by_bench[bench].append(r['time_s'])
        
        for bench, times in sorted(by_bench.items()):
            if times:
                avg_time = statistics.mean(times) if times else None
                if avg_time:
                    print(f"   {bench:<25}: {avg_time*1000:8.3f} ms")
        
        print()

def compare_benchmarks(results):
    """Compara diferentes benchmarks"""
    
    print("\n" + "="*80)
    print("COMPARACIÓN DE BENCHMARKS".center(80))
    print("="*80 + "\n")
    
    # Agrupar por benchmark
    benchmarks = {}
    for r in results:
        name = r['benchmark'].split('/')[0] if '/' in r['benchmark'] else r['benchmark']
        if name not in benchmarks:
            benchmarks[name] = []
        benchmarks[name].append(r)
    
    # Calcular promedios
    print(f"{'Benchmark':<25} {'Tiempo Prom':<15} {'Energía Prom':<15} {'Potencia Prom':<15}")
    print("-" * 80)
    
    for bench_name, data in sorted(benchmarks.items()):
        times = [r['time_s'] for r in data if r['time_s'] is not None and r['time_s'] > 0]
        energies = [r['energy_J'] for r in data if r['energy_J'] is not None and r['energy_J'] > 0]
        powers = [r['power_avg_W'] for r in data if r['power_avg_W'] is not None and r['power_avg_W'] > 0]
        
        avg_time = f"{statistics.mean(times)*1000:.3f} ms" if times else "N/A"
        avg_energy = f"{statistics.mean(energies):.6f} J" if energies else "N/A"
        avg_power = f"{statistics.mean(powers):.3f} W" if powers else "N/A"
        
        print(f"{bench_name:<25} {avg_time:<15} {avg_energy:<15} {avg_power:<15}")
    
    print()

def find_best_configs(results):
    """Encuentra las mejores configuraciones por métrica"""
    
    print("\n" + "="*80)
    print("MEJORES CONFIGURACIONES".center(80))
    print("="*80 + "\n")
    
    # Filtrar resultados válidos
    valid_results = [r for r in results if r['time_s'] is not None and r['time_s'] > 0]
    
    if not valid_results:
        print("⚠️  No hay resultados válidos")
        return
    
    # Menor tiempo
    best_time = min(valid_results, key=lambda x: x['time_s'])
    print(f"⚡ Menor tiempo: {best_time['time_s']*1000:.3f} ms")
    print(f"   Benchmark: {best_time['benchmark']}")
    print()
    
    # Menor energía
    valid_energy = [r for r in valid_results if r['energy_J'] is not None and r['energy_J'] > 0]
    if valid_energy:
        best_energy = min(valid_energy, key=lambda x: x['energy_J'])
        print(f"🔋 Menor energía: {best_energy['energy_J']:.6f} J")
        print(f"   Benchmark: {best_energy['benchmark']}")
        print()
    
    # Mejor EDP
    valid_edp = [r for r in valid_results if r['edp'] is not None and r['edp'] > 0]
    if valid_edp:
        best_edp = min(valid_edp, key=lambda x: x['edp'])
        print(f"⚖️  Mejor EDP: {best_edp['edp']:.2e}")
        print(f"   Benchmark: {best_edp['benchmark']}")
        print()

def main():
    """Función principal"""
    
    print("\n" + "="*80)
    print("ANALIZADOR DE RESULTADOS - benchmark_monitor C++".center(80))
    print("="*80)
    
    # Cargar resultados
    results = load_results()
    
    print(f"\n📊 Total de resultados: {len(results)}")
    
    # Análisis
    analyze_by_benchmark(results)
    analyze_by_size(results)
    compare_benchmarks(results)
    find_best_configs(results)
    
    print("="*80)
    print("✅ Análisis completado".center(80))
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
