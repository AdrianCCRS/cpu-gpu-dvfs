Proyecto 10: Ajuste Dinámico de Frecuencia (DVFS) en Sistemas
Heterogéneos CPU–GPU Mediante Aprendizaje Automático
Descripción
Este proyecto investiga técnicas de Dynamic Voltage and Frequency Scaling (DVFS) para optimizar el trade-off rendimiento–energía en aplicaciones HPC híbridas
CPU–GPU. Se desarrollará un runtime que, basado en un modelo de machine learning entrenado con características de la carga, ajuste en tiempo real las frecuencias
de CPU y GPU.
Objetivo general
Diseñar e implementar un sistema autoadaptativo que utilice aprendizaje automático para ajustar dinámicamente las frecuencias de CPU y GPU, minimizando el
Energy-Delay Product (EDP) en aplicaciones HPC híbridas.
Objetivos específicos
Implementar microbenchmarks de CPU (AVX-512, acceso a memoria) y GPU (kernels CUDA básicos) que midan latencia, throughput y consumo energético.
Desarrollar scripts para cambiar dinámicamente las frecuencias de CPU (cpufreq) y GPU (NVML) y recopilar métricas de rendimiento y energía.
Generar un dataset variado cubriendo combinaciones de frecuencias y tamaños de problema, extrayendo features como IPC, cache-misses y SM-util.
Entrenar y validar modelos de ML (Random Forest, XGBoost) para predecir la configuración de frecuencia óptima según la fase de cómputo.
Implementar un runtime ligero (C++/Python) que monitorice métricas en línea, consulte el modelo ML y aplique DVFS con overhead < 5 ms.
Evaluar mejoras de EDP y speedup en kernels de referencia (GEMM, stencil 3D, SpMV) frente a governors estáticos.
Documentar recomendaciones de políticas DVFS en arquitecturas heterogéneas y redactar un manuscrito IMRAD con resultados reproducibles.
Alcance
Plataformas de prueba:
CPU Intel con cpufreq y RAPL
GPU NVIDIA con NVML
Workloads:
Microbenchmarks CPU (vector dot, memcpy)
Kernels GPU (pequeños GEMM, stencil 3D, SpMV)
Rango de frecuencias explorado:
CPU: 1.2–3.8 GHz
GPU: 500–1500 MHz
Métricas recogidas: latencia, throughput, consumo energético y Energy-Delay Product
Entregables:
Scripts de benchmarking y dataset de ejecuciones
Modelos ML entrenados y validados
Código del runtime DVFS
Jupyter Notebooks con análisis y visualizaciones
Manuscrito IMRAD listo para congreso o revista de HPC
Metodología y cronograma (16 semanas)
Semanas Tareas y Temas Recursos de Aprendizaje
1–2
• Fundamentos de DVFS en CPU (governors, cpufreq) y GPU (NVML)
• Instalación de herramientas de medición (RAPL, NVML)
• Intel® 64 and IA-32 Architectures Optimization
Manual, Cap. “Power and Energy”
• NVIDIA NVML API Reference
• Linux cpufreq How-To
3–4
• Diseño de microbenchmarks CPU (AVX-512 dot, memcpy)
• Diseño de microbenchmarks GPU (pequeño GEMM, stencil)
• Sanders & Kandrot, CUDA by Example, Cap. 2–3
• Chandra et al.,Using OpenMP, Cap. 2 sobre
vectores y memoria
5–6
• Instrumentación automática: scripts Python/C++ para cambiar
frecuencias y medir latencia, throughput y energía
• Python: subprocess para cpufreq-set y bindings
NVML
• RAPL & perf tutorial
7–8
• Generación de dataset: ejecutar microbenchmarks variando
frecuencia CPU (1.2–3.8 GHz) y GPU (500–1500 MHz)
• Pandas & CSV I/O tutorial
• Matplotlib para visualización de superficie
rendimiento-energía
9–10
• Entrenamiento de modelos ML:
– Selección de features (IPC, cache-misses, SM-util)
– Random Forest y XGBoost
• Géron, Hands-On ML with Scikit-Learn, Cap. 4–6
• Hastie et al.,The Elements of Statistical
Learning, Cap. sobre árboles y boosting
11 • Validación cruzada y ajuste de hiperparámetros con Optuna • Optuna Documentation (pruning, multi-objective)
12
• Implementación del runtime DVFS:
– Monitor de métricas en C++⇄Python
– Aplicación de frecuencia predicha antes de cada kernel
• The Rust Programming Language, Cap. 15 (si se
usa Rust para runtime)
• Tutorial “Embedding Python in C++” (Medium)
13–14
• Integración con kernels de referencia (GEMM, stencil 3D, SpMV): medir
EDP con política ML vs governors estáticos
• Xiang et al., “AutoTVM” (OSDI 2018) para tuning
de GEMM
• Mittal et al., “Stencil Computation Optimization”
Cap. sobre memoria
15
• Análisis estadístico de resultados:
– Comparativa EDP, speedup, consumo
– Pruebas t-test/ANOVA
• Bruce & Gedeck,Practical Statistics for Data
Scientists, Cap. 5–6
16
• Redacción del manuscrito (IMRAD): introducción, metodología,
resultados y discusión
• Preparación de figuras/tablas y envío
• Day & Gastel,How to Write and Publish a
Scientific Paper
• Plantillas LaTeX de ACM/IEEE
Semanas Tareas y Temas Recursos de Aprendizaje
Detalle de aprendizaje por fase
Semanas 1–2: Fundamentos de DVFS y Medición de Energía
Estudiar governors de Linux ( performance , powersave , ondemand ).
Configurar RAPL y NVML para leer consumo en CPU y GPU.
Semanas 3–4: Microbenchmarks de Caracterización
Implementar kernels cortos para medir IPC, ancho de banda y occupancy.
Validar corrección de los scripts de frecuencia antes de automatizar.
Semanas 5–6: Automatización de Experimentos
Desarrollar scripts que varíen frecuencias, lancen microbenchmarks y registren métricas en CSV.
Visualizar primeros mapas 3D de rendimiento vs energía.
Semanas 7–8: Generación de Dataset para ML
Ejecutar barridos completos de frecuencias en distintos tamaños de entrada.
Limpiar y normalizar datos con pandas.
Semanas 9–10: Entrenamiento de Modelos Predictivos
Extraer features de rendimiento y consumo para cada experimento.
Entrenar Random Forest y XGBoost para predecir frecCPU y frecGPU simultáneamente.
Semana 11: Validación y Ajuste de Hiperparámetros
Realizar k-fold cross-validation, usar Optuna para optimizar profundidad de árboles y tasa de aprendizaje.
Evaluar correlación de features e importancia.
Semana 12: Desarrollo del Runtime DVFS
Construir un componente que, leyendo métricas online vía PAPI/NVML, consulte el modelo y aplique frecuencias recomendadas.
Medir overhead de decisión y asegurar latencia < 5 ms.
Semanas 13–14: Evaluación en Kernels de Referencia
Integrar el runtime en ejecuciones de GEMM, stencil 3D y SpMV.
Comparar EDP y speedup contra governors estáticos.
Semana 15: Análisis Estadístico
Aplicar t-test y ANOVA para demostrar mejoras significativas de la política ML.
Generar gráficos comparativos de EDP y rendimiento.
Semana 16: Documentación y Publicación
Redactar el artículo IMRAD, enfocando en la novedad del ajuste DVFS predictivo.
Preparar figuras, tablas de Pareto y enviar a conferencia o revista de HPC.