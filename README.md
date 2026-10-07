# Evaluación de datos — Accidentabilidad laboral en Chile

Proyecto de tratamiento y cruce de datos que relaciona **accidentes del trabajo y de trayecto (SUSESO)** con la **población ocupada por rama económica (INE, Encuesta Nacional de Empleo)**, para calcular la **tasa de accidentabilidad** por región y por sector económico.

---

## 1. Contenido del proyecto

| Archivo | Descripción |
|---|---|
| `tratado.py` | Script principal: carga, homologa, cruza ambas fuentes y genera los resultados |
| `data/accidentes_trabajo_trayecto_datos_gob.csv` | Fuente 1 — Accidentes laborales (SUSESO, portal datos.gob.cl), ~278 MB |
| `data/ENE_OCU_RAMA_06102026154800949.csv` | Fuente 2 — Ocupados por rama económica (INE-ENE), ~1,2 MB |
| `data/resultado_region.csv` | Salida 1 — Tasa de accidentabilidad por región (año 2024) |
| `data/resultado_sector.csv` | Salida 2 — Tasa de accidentabilidad por sector económico (año 2024) |

---

## 2. Las dos fuentes de datos

### Fuente 1 — Accidentes SUSESO (`accidentes_trabajo_trayecto_datos_gob.csv`)

- **Origen:** Superintendencia de Seguridad Social (SUSESO), dataset público de datos.gob.cl.
- **Unidad de análisis:** registro agregado *mensual* de accidentes, desglosado por región, actividad económica, origen, tamaño de empresa, año, agente, forma del accidente, nacionalidad, parte del cuerpo, organismo administrador y tramo de edad.
- **Separador:** `|` (pipe).
- **Cobertura temporal:** enero 2015 – mayo 2026 (1.355.529 registros, ~2,53 millones de accidentes acumulados).
- **Columnas clave para el cruce:** `Región` y `Actividad económica CIIU 2007`.
- **Variable de medida:** `Total` (nº de accidentes del registro; es la suma de `Mujer` + `Hombre` + `Sin información`).
- **Origen del accidente:** dos valores — `Accidentes del trabajo` (en el puesto de trabajo) y `Accidentes de trayecto` (entre la casa y el trabajo). **Ambos se incluyen** en el análisis.

### Fuente 2 — Ocupados INE-ENE (`ENE_OCU_RAMA_...csv`)

- **Origen:** Instituto Nacional de Estadísticas (INE), indicador *"Employed by branch of economic activity (CIIU Rev4 según Caenes)"*, ENE con proyecciones base 2017.
- **Unidad de análisis:** ocupados (en **miles de personas**) por trimestre móvil, región, rama económica y sexo.
- **Cobertura temporal:** 4 trimestres móviles de 2024 (dic-feb, ene-mar, feb-abr, mar-may).
- **Cobertura geográfica:** total nacional + 13 regiones (**no incluye** Los Lagos, Aysén ni Magallanes).
- **Columnas clave para el cruce:** `Region` (nombres en inglés) y `DTI_CL_RAMA_ECO` (códigos CAENES 2.0).
- **Variable de medida:** `Value` (miles de ocupados; se multiplica ×1.000 para obtener personas).

---

## 3. ¿Cómo se relacionan los datos? (el cruce)

Las dos fuentes miden cosas distintas y con clasificaciones distintas, por lo que **no se pueden cruzar directamente**. La relación se construye en tres pasos:

### Paso 1 — Homologación de las claves

| Dimensión | SUSESO (accidentes) | ENE-INE (ocupados) | Solución aplicada |
|---|---|---|---|
| **Geográfica** | `Región` en español (p. ej. `De Metropolitana de Santiago`) | `Region` en inglés (p. ej. `Region Metropolitana de Santiago`) | Diccionario `mapa_regiones` INE→SUSESO |
| **Sectorial** | `Actividad económica CIIU 2007` (17 categorías) | `DTI_CL_RAMA_ECO` CAENES 2.0 (21 ramas) | Diccionarios `mapa_sectores_ene` (por código) y `mapa_sectores_acc` |

En la dimensión sectorial, la clasificación CIIU 2007 de SUSESO es *más antigua* que la CAENES 2.0 del INE: varias ramas CAENES se agrupan en una sola categoría SUSESO. Por eso en el script las ramas del INE se **agregan antes del cruce**:

| Categoría SUSESO (CIIU 2007) | Ramas CAENES 2.0 (INE) que la componen |
|---|---|
| Actividades inmobiliarias, empresariales y de alquiler | L (Inmobiliarias) + M (Profesionales y científicas) + N (Administrativas y de apoyo) |
| Transporte, almacenamiento y comunicaciones | H (Transporte) + J (Información y comunicaciones) |
| Suministro de electricidad, gas y agua | D (Electricidad y gas) + E (Agua) |
| Otras actividades de servicios | R (Artes y entretenimiento) + S (Otros servicios) |
| Agricultura, ganadería, silvicultura y pesca | A (incluye pesca; SUSESO la trae en 2 categorías que se suman) |

### Paso 2 — Comparabilidad temporal

- Los accidentes cubren 2015–2026, pero la ENE disponible es solo de 2024.
- Para que la tasa sea **anual y comparable**, el script filtra los accidentes al año **2024** (`ANIO_ANALISIS = 2024`).
- El denominador es el promedio de los 4 trimestres móviles ENE de 2024.

### Paso 3 — Cruce de agregación N:1 y cálculo de la tasa

```
  SUSESO (lado "muchos")                     INE-ENE (lado "uno")
  1,36 M registros mensuales                 3.864 registros trimestrales
        │                                          │
        │ Filtro: Año = 2024                       │ Filtro: rama total / sexo Total
        │ groupby(Región o Sector).sum('Total')    │ groupby(Región o Sector).mean('Value'×1000)
        ▼                                          ▼
   NUMERADOR  ────────────── MERGE (inner) ────────────── DENOMINADOR
   (accidentes 2024 por clave)                (ocupados promedio 2024 por clave)
                          │
                          ▼
        Tasa = (Accidentes / Ocupados) × 100.000
```

Es una relación de **muchos-a-uno**: muchos registros de accidentes se agregan a una sola fila por región (o sector), que se une con la única fila de ocupados de esa misma clave. El `merge` es `inner`: si una clave no existe en ambas fuentes, queda fuera del resultado (el script imprime un diagnóstico indicando qué claves se excluyen y por qué).

---

## 4. Métrica calculada

> **Tasa de accidentabilidad** = (Accidentes del año 2024, del trabajo y de trayecto / Ocupados promedio 2024) × 100.000

Se interpreta como *accidentes por cada 100.000 personas ocupadas durante un año*. Se calcula en dos niveles:

- **Geográfico:** `resultado_region.csv` (numerador = accidentes por región; denominador = ocupados de la rama total por región).
- **Sectorial:** `resultado_sector.csv` (numerador = accidentes por actividad económica; denominador = ocupados por rama a nivel nacional).

Además se incluye la **participación porcentual** de cada clave en el total nacional de accidentes 2024 (216.647 accidentes).

---

## 5. Resultados 2024

### Tasa de accidentabilidad por región (por cada 100.000 ocupados)

| Región | Accidentes 2024 | % del total | Ocupados | Tasa ×100k |
|---|---:|---:|---:|---:|
| De Valparaíso | 24.788 | 11,4% | 915.687 | **2.707,0** |
| De Metropolitana de Santiago | 100.344 | 46,3% | 4.128.461 | **2.430,5** |
| Del Libertador Gral. Bdo. O'Higgins | 10.669 | 4,9% | 454.878 | **2.345,5** |
| Del Biobío | 16.250 | 7,5% | 714.580 | **2.274,1** |
| De La Araucanía | 9.511 | 4,4% | 433.529 | **2.193,9** |
| De Los Ríos | 3.918 | 1,8% | 185.053 | 2.117,2 |
| De Antofagasta | 7.132 | 3,3% | 342.728 | 2.080,9 |
| De Atacama | 3.025 | 1,4% | 150.557 | 2.009,2 |
| Del Maule | 10.532 | 4,9% | 529.920 | 1.987,5 |
| De Coquimbo | 6.331 | 2,9% | 373.087 | 1.696,9 |
| De Arica y Parinacota | 1.926 | 0,9% | 115.110 | 1.673,2 |
| De Ñuble | 3.591 | 1,7% | 221.444 | 1.621,6 |
| De Tarapacá | 2.963 | 1,4% | 191.092 | 1.550,6 |

*Excluidas por no tener datos de ocupados en la ENE descargada: De Los Lagos (5,0% de los accidentes), De Magallanes (1,5%), De Aysén (0,8%).*

### Tasa de accidentabilidad por sector económico (por cada 100.000 ocupados)

| Sector | Accidentes 2024 | % del total | Ocupados | Tasa ×100k |
|---|---:|---:|---:|---:|
| Actividades inmobiliarias, empresariales y de alquiler | 28.869 | 13,3% | 238.037 | **12.127,9** |
| Otras actividades de servicios | 13.405 | 6,2% | 228.662 | **5.862,4** |
| Transporte, almacenamiento y comunicaciones | 16.272 | 7,5% | 399.417 | **4.073,9** |
| Actividades de alojamiento y de servicio de comidas | 14.449 | 6,7% | 431.949 | **3.345,1** |
| Construcción | 22.700 | 10,5% | 736.060 | **3.084,0** |
| Administración pública y defensa | 16.660 | 7,7% | 574.178 | 2.901,5 |
| Industria manufacturera | 23.100 | 10,7% | 872.432 | 2.647,8 |
| Agricultura, ganadería, silvicultura y pesca | 15.505 | 7,2% | 591.906 | 2.619,5 |
| Organizaciones y órganos extraterritoriales | 63 | 0,0% | 2.919 | 2.158,1 |
| Actividades de atención de la salud y asistencia social | 13.900 | 6,4% | 693.828 | 2.003,4 |
| Enseñanza | 14.798 | 6,8% | 753.829 | 1.963,0 |
| Comercio al por mayor y al por menor | 29.853 | 13,8% | 1.790.043 | 1.667,7 |
| Actividades financieras y de seguros | 2.662 | 1,2% | 192.108 | 1.385,7 |
| Hogares privados con servicio doméstico | 2.927 | 1,4% | 275.483 | 1.062,5 |
| Suministro de electricidad, gas y agua | 594 | 0,3% | 61.866 | 960,1 |
| Explotación de minas y canteras | 890 | 0,4% | 285.005 | 312,3 |

---

## 6. Correcciones aplicadas respecto a la versión anterior del script

La versión original de `tratado.py` tenía cuatro problemas que distorsionaban la relación entre las fuentes. Todos fueron corregidos:

1. **Regiones perdidas en el cruce geográfico.** El diccionario homologaba la RM como `'Metropolitana de Santiago'` y O'Higgins como `"Del Libertador Gral. Bernardo O'Higgins"`, pero el accidentario usa `'De Metropolitana de Santiago'` y `"Del Libertador Gral. Bdo. O'higgins"`. Al ser un `merge` interno, **la Región Metropolitana (46% de los accidentes del país) y O'Higgins desaparecían silenciosamente** del resultado (quedaban solo 11 regiones). Corregido usando los nombres exactos de SUSESO.

2. **Incompatibilidad entre clasificaciones sectoriales.** El accidentario usa CIIU 2007 y la ENE usa CAENES 2.0. La categoría SUSESO *"Actividades inmobiliarias, empresariales y de alquiler"* equivale a **tres** ramas del INE (L+M+N), pero el script original la comparaba solo con la rama L (Inmobiliarias), produciendo una tasa imposible (370.078 accidentes por 100.000 ocupados, es decir, 3,7 accidentes por trabajador). Corregido agregando las ramas del INE (L+M+N, H+J, D+E, R+S) antes del cruce. También se rescataron `Administración pública`, `Otras actividades de servicios` y `Hogares privados con servicio doméstico`, que antes nunca cruzaban por nombres distintos (el resultado pasaba de 11 a 16 sectores).

3. **Desajuste temporal (numerador vs. denominador).** El script original sumaba **11 años** de accidentes (2015–2026) y los dividía por los ocupados de **un solo trimestre de 2024**, inflando las tasas ~11 veces (p. ej. Valparaíso: 28.128 en vez de 2.707). Corregido filtrando los accidentes al año 2024, comparable con los trimestres móviles de la ENE: la tasa resultante es ahora **anual**.

4. **Robustez del mapeo.** La homologación sectorial del INE ahora se hace por **código** (`DTI_CL_RAMA_ECO`) en lugar de por nombre, evitando fallos por espacios finales o diferencias de acentos (p. ej. `'Mining '` y `'Public administration '` traen espacio final en el archivo del INE).

## 7. Limitaciones y supuestos (para considerar en la evaluación)

- **Cobertura geográfica de la ENE descargada:** solo 13 regiones. Los Lagos, Aysén y Magallanes (~7,3% de los accidentes) quedan fuera del análisis por carecer de denominador.
- **Cobertura temporal de la ENE:** 4 trimestres móviles que se solapan (dic-feb a mar-may de 2024); su promedio aproxima la ocupación del primer semestre de 2024.
- **Homologación CIIU 2007 ↔ CAENES 2.0:** es una correspondencia *n-a-1* aproximada; no es posible desagregar los accidentes SUSESO a la granularidad de las 21 ramas CAENES.
- **"Actividades inmobiliarias, empresariales y de alquiler":** en esta categoría SUSESO se declaran muchos accidentes de trabajadores de empresas de servicios transitorios (suministro de personal, aseo, seguridad), lo que explica su tasa excepcionalmente alta (12.128); debe leerse como *servicios empresariales*, no como sector inmobiliario puro.
- **Minería:** su baja tasa (312) se explica porque el empleo minero es muy alto y de gran empresa con fuerte fiscalización; los accidentes se atribuyen a la región/actividad del empleador.
- **`'Sin información'`** en region del accidentario (2 accidentes en 2024) se excluye del cruce.
- La ENE usa proyecciones de población base 2017; el accidentario incluye accidentes del trabajo y de trayecto (ambos sumados).

## 8. Cómo ejecutar

### Pauta para presentar el análisis

La [pauta de presentación](./Pauta_presentacion.md) recomienda qué incluir en cada
lámina: títulos, gráficos, cifras destacadas, capturas del dashboard y limitaciones.

### Dashboard interactivo

Instala las dependencias del proyecto e inicia la aplicación:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

Al abrirse, el dashboard genera los resultados mediante `tratado.py` si no existen
o si las fuentes han cambiado. El primer cálculo puede tardar porque el archivo
SUSESO ocupa aproximadamente 278 MB. La aplicación presenta indicadores generales,
gráficos y tablas comparables por región y sector; también permite cambiar la métrica
y el número de categorías mostradas.

### Ejecución del tratamiento por separado

```powershell
python tratado.py
```

Requisitos: Python 3.10+ y pandas. El script lee los CSV desde la carpeta `data/` y sobrescribe `resultado_region.csv` y `resultado_sector.csv`. Para analizar otro año, cambiar la constante `ANIO_ANALISIS` (los accidentes están disponibles de 2015 a mayo de 2026; la ENE descargada solo es comparable con 2024).
