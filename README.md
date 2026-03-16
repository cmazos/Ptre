# Hydrogeochemical Scale Predictor App 💧

Esta aplicación web interactiva desarrollada en Python utilizando Streamlit permite realizar simulaciones hidrogeoquímicas para evaluar tendencias de incrustación mineral (Scale) en aguas de producción e inyección de campos de hidrocarburos.

## Características Principales

1. **Entrada y Balance Iónico**: Ingreso de la composición química (cationes y aniones en mg/L) de hasta 3 tipos de agua.
2. **Auto-Ajuste (Make-up)**: Cálculo automático del Error de Balance de Cargas (CBE). Si el CBE supera el $\pm 5\%$, el backend se auto-ajusta usando $Na^+$ o $Cl^-$ para garantizar neutralidad eléctrica.
3. **Módulo de Mezcla**: Posibilidad de introducir fracciones volumétricas para la mezcla de múltiples aguas, calculando la concentración resultante con balances de masa.
4. **Simulación Termodinámica**: Utiliza el motor avanzado **PHREEQC** (mediante `phreeqpython`) con la base de datos de alta salinidad `pitzer.dat`.
5. **Visualización Técnica**:
   - Generación de diagramas de Stiff interactivos.
   - Gráficas de tendencia de Índices de Saturación (SI) para Calcita, Barita, Celestita y Anhidrita/Yeso, evaluando un rango iterativo de Presión y Temperatura.

## Instrucciones de Instalación

1. Clona el repositorio e ingresa a la carpeta del proyecto.
2. Se recomienda crear un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecuta la aplicación:
   ```bash
   streamlit run app.py
   ```

## Ejecución en Google Colab

Si no tienes Python localmente, puedes correr la aplicación directamente desde tu navegador utilizando Google Colab y `localtunnel`:

1. Abre un nuevo [Google Colab Notebook](https://colab.research.google.com/).
2. Sube todos los archivos del proyecto (`app.py`, `backend.py`, `visualizations.py`, `requirements.txt`) a la carpeta de archivos (ícono de carpeta en el panel izquierdo).
3. En una celda de código, instala las dependencias y `localtunnel`:
   ```python
   !pip install -r requirements.txt
   !npm install localtunnel
   ```
4. En otra celda, ejecuta la aplicación en segundo plano y exponla con `localtunnel`. Extraeremos la IP temporal para que la uses como contraseña:
   ```python
   import urllib
   print("Contraseña para el túnel (IP local):", urllib.request.urlopen('https://ipv4.icanhazip.com').read().decode('utf8').strip("\n"))

   !streamlit run app.py & npx localtunnel --port 8501
   ```
5. Haz clic en el enlace `your url is: https://...` generado. La página te pedirá una **End Tunnel Password**, donde debes ingresar la **Contraseña/IP local** que se imprimió en el paso anterior. ¡Listo, ya puedes usar la aplicación interactiva en Streamlit!


## Fundamentación Científica

Los algoritmos y aproximaciones termodinámicas en esta aplicación se fundamentan en literatura indexada y software de amplio reconocimiento en la evaluación geoquímica en la industria petrolera:

- **Motor de Simulación Geoquímica:**  
  Parkhurst, D. L., & Appelo, C. A. J. (2013). *Description of input and examples for PHREEQC version 3—A computer program for speciation, batch-reaction, one-dimensional transport, and inverse geochemical calculations*. U.S. Geological Survey Techniques and Methods, book 6, chap. A43.
  
- **Modelo Termodinámico para Salmueras (Alta Salinidad):**  
  Pitzer, K. S. (1973). *Thermodynamics of electrolytes. I. Theoretical basis and general equations*. The Journal of Physical Chemistry, 77(2), 268-277. [DOI: 10.1021/j100621a026](https://doi.org/10.1021/j100621a026)
  
- **Evaluación de Daño a la Formación (Incrustaciones):**  
  Moghadasi, J., Jamialahmadi, M., Müller-Steinhagen, H., & Sharif, A. (2003). *Scale formation in oil reservoir and production equipment during water injection*. Society of Petroleum Engineers - SPE European Formation Damage Conference. [DOI: 10.2118/82215-MS](https://doi.org/10.2118/82215-MS)
