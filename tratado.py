# -*- coding: utf-8 -*-
"""
tratado.py - Relación entre accidentabilidad laboral (SUSESO) y ocupación (INE-ENE)
=================================================================================

FUENTES DE DATOS Y SU RELACIÓN
------------------------------
1) data/accidentes_trabajo_trayecto_datos_gob.csv   (SUSESO, datos.gob.cl)
   - Unidad de análisis: registro agregado MENSUAL de accidentes (del trabajo
     y de trayecto) por región, actividad económica, origen, año, etc.
   - Claves de cruce: 'Región' y 'Actividad económica CIIU 2007'
   - Variable de medida: 'Total' (nº de accidentes del registro)
   - Cobertura temporal: 2015-01 a 2026-05 (11+ años)

2) data/ENE_OCU_RAMA_06102026154800949.csv   (INE, Encuesta Nacional de Empleo)
   - Unidad de análisis: ocupados (en MILES de personas) por trimestre móvil,
     región, rama económica (CIIU Rev.4 / CAENES 2.0) y sexo.
   - Claves de cruce: 'Region' y 'DTI_CL_RAMA_ECO'
   - Variable de medida: 'Value' (miles de ocupados)
   - Cobertura temporal: 4 trimestres móviles de 2024 (dic-feb ... mar-may)

TIPO DE RELACIÓN: cruce de agregación muchos-a-uno (N:1)
   - Lado "muchos": accidentes -> se agregan con SUM('Total') por clave.
   - Lado "uno": ocupados -> se promedian los 4 trimestres por clave.
   - Resultado: TASA DE ACCIDENTABILIDAD = (accidentes / ocupados) * 100.000

Las dos dimensiones de cruce son:
   A) GEOGRÁFICA  : Región (homologación de nombres INE-inglés -> SUSESO-español)
   B) SECTORIAL   : Actividad económica (homologación CIIU 2007 <-> CAENES 2.0)

COMPARABILIDAD TEMPORAL: los accidentes se filtran al AÑO 2024, ya que la ENE
disponible corresponde a trimestres móviles de 2024. La tasa resultante es,
por lo tanto, ANUAL (accidentes 2024 por cada 100.000 ocupados promedio 2024).
"""

import os
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ------------------------------------------------------------------
# 1. RUTAS DE LOS ARCHIVOS (carpeta 'data')
# ------------------------------------------------------------------
ruta_accidentes = os.path.join('data', 'accidentes_trabajo_trayecto_datos_gob.csv')
ruta_ene = os.path.join('data', 'ENE_OCU_RAMA_06102026154800949.csv')

print("--- Cargando fuentes de datos ---")
# El archivo de accidentes pesa ~278 MB: se leen solo las columnas necesarias.
df_acc = pd.read_csv(
    ruta_accidentes,
    sep='|',
    usecols=['Región', 'Actividad económica CIIU 2007', 'Año', 'Origen', 'Total']
)
df_ene = pd.read_csv(ruta_ene)
print(f"Accidentes SUSESO: {len(df_acc):,} registros ({df_acc['Año'].min()}-{df_acc['Año'].max()})")
print(f"Ocupados ENE-INE : {len(df_ene):,} registros ({df_ene['DTI_CL_TRIMESTRE_MOVIL'].nunique()} trimestres móviles)")

# ------------------------------------------------------------------
# 2. HOMOLOGACIÓN GEOGRÁFICA (nombres INE en inglés -> nombres SUSESO)
#    Se usan EXACTAMENTE los nombres del archivo SUSESO, incluidos
#    'De Metropolitana de Santiago' y "Del Libertador Gral. Bdo. O'higgins".
# ------------------------------------------------------------------
mapa_regiones = {
    'Nationwide total': 'Total Nacional',
    'Region of Arica y Parinacota': 'De Arica y Parinacota',
    'Region of Tarapacá': 'De Tarapacá',
    'Region of Antofagasta': 'De Antofagasta',
    'Region of Atacama': 'De Atacama',
    'Region of Coquimbo': 'De Coquimbo',
    'Region of Valparaíso': 'De Valparaíso',
    'Region Metropolitana de Santiago': 'De Metropolitana de Santiago',
    "Region of Libertador Gral. Bernardo O'Higgins": "Del Libertador Gral. Bdo. O'higgins",
    'Region of Maule': 'Del Maule',
    'Region of Ñuble': 'De Ñuble',
    'Region of Biobío': 'Del Biobío',
    'Region of La Araucanía': 'De La Araucanía',
    'Region of Los Ríos': 'De Los Ríos',
}
df_ene['Region_ES'] = df_ene['Region'].map(mapa_regiones)

# ------------------------------------------------------------------
# 3. HOMOLOGACIÓN SECTORIAL (CAENES 2.0 del INE -> CIIU 2007 de SUSESO)
#    Mapeo por CÓDIGO (robusto frente a espacios/acentos en los nombres).
#    Las ramas CAENES L+M+N, H+J, D+E y R+S se AGREGAN porque en la
#    clasificación CIIU 2007 del accidentario forman categorías únicas.
# ------------------------------------------------------------------
mapa_sectores_ene = {
    'ISIC4_CAENES12_A': 'Agricultura, ganadería, silvicultura y pesca',
    'ISIC4_CAENES12_B': 'Explotación de minas y canteras',
    'ISIC4_CAENES12_C': 'Industria manufacturera',
    'ISIC4_CAENES12_D': 'Suministro de electricidad, gas y agua',
    'ISIC4_CAENES12_E': 'Suministro de electricidad, gas y agua',
    'ISIC4_CAENES12_F': 'Construcción',
    'ISIC4_CAENES12_G': 'Comercio al por mayor y al por menor',
    'ISIC4_CAENES12_H': 'Transporte, almacenamiento y comunicaciones',
    'ISIC4_CAENES12_I': 'Actividades de alojamiento y de servicio de comidas',
    'ISIC4_CAENES12_J': 'Transporte, almacenamiento y comunicaciones',
    'ISIC4_CAENES12_K': 'Actividades financieras y de seguros',
    'ISIC4_CAENES12_L': 'Actividades inmobiliarias, empresariales y de alquiler',
    'ISIC4_CAENES12_M': 'Actividades inmobiliarias, empresariales y de alquiler',
    'ISIC4_CAENES12_N': 'Actividades inmobiliarias, empresariales y de alquiler',
    'ISIC4_CAENES12_O': 'Administración pública y defensa',
    'ISIC4_CAENES12_P': 'Enseñanza',
    'ISIC4_CAENES12_Q': 'Actividades de atención de la salud humana y de asistencia social',
    'ISIC4_CAENES12_R': 'Otras actividades de servicios',
    'ISIC4_CAENES12_S': 'Otras actividades de servicios',
    'ISIC4_CAENES12_T': 'Hogares privados con servicio doméstico',
    'ISIC4_CAENES12_U': 'Organizaciones y órganos extraterritoriales',
}
df_ene['Sector_ES'] = df_ene['DTI_CL_RAMA_ECO'].map(mapa_sectores_ene)

# Lado SUSESO: nombres exactos del accidentario -> categoría homologada
mapa_sectores_acc = {
    'Agricultura, ganadería, caza y silvicultura': 'Agricultura, ganadería, silvicultura y pesca',
    'Pesca': 'Agricultura, ganadería, silvicultura y pesca',
    'Explotación de minas y canteras': 'Explotación de minas y canteras',
    'Industrias manufactureras': 'Industria manufacturera',
    'Suministro de electricidad, gas y agua': 'Suministro de electricidad, gas y agua',
    'Construcción': 'Construcción',
    'Comercio, reparación de vehículos y otros': 'Comercio al por mayor y al por menor',
    'Transporte, almacenamiento y comunicaciones': 'Transporte, almacenamiento y comunicaciones',
    'Hoteles y restaurantes': 'Actividades de alojamiento y de servicio de comidas',
    'Intermediación financiera': 'Actividades financieras y de seguros',
    'Actividades inmobiliarias, empresariales y de alquiler': 'Actividades inmobiliarias, empresariales y de alquiler',
    'Administración pública y defensa': 'Administración pública y defensa',
    'Enseñanza': 'Enseñanza',
    'Servicios sociales y de salud': 'Actividades de atención de la salud humana y de asistencia social',
    'Otras actividades de servicios comunitarios, sociales y personales': 'Otras actividades de servicios',
    'Hogares privados con servicio doméstico': 'Hogares privados con servicio doméstico',
    'Organizaciones y órganos extraterritoriales': 'Organizaciones y órganos extraterritoriales',
}
df_acc['Sector_ES'] = df_acc['Actividad económica CIIU 2007'].map(mapa_sectores_acc)

# ------------------------------------------------------------------
# 4. COMPARABILIDAD TEMPORAL: solo accidentes del AÑO 2024
#    (la ENE disponible corresponde a 4 trimestres móviles de 2024)
# ------------------------------------------------------------------
ANIO_ANALISIS = 2024
df_acc_anio = df_acc[df_acc['Año'] == ANIO_ANALISIS].copy()
total_acc_nacional = df_acc_anio['Total'].sum()
print(f"\nAccidentes {ANIO_ANALISIS} (trabajo + trayecto): {total_acc_nacional:,}")

# ------------------------------------------------------------------
# 5. ANÁLISIS 1: TASA DE ACCIDENTABILIDAD POR REGIÓN
#    Numerador  : SUM('Total') de accidentes 2024 por región (SUSESO)
#    Denominador: ocupados promedio 2024 por región     (ENE, en personas)
# ------------------------------------------------------------------
acc_region = (
    df_acc_anio.groupby('Región')['Total'].sum()
    .reset_index()
    .rename(columns={'Total': 'Accidentes'})
)

ene_totales = df_ene[
    (df_ene['DTI_CL_RAMA_ECO'] == 'ISIC4_CAENES12_TOTAL')
    & (df_ene['Sex'] == 'Total')
    & (df_ene['Region_ES'] != 'Total Nacional')
].copy()
ene_totales['Ocupados'] = ene_totales['Value'] * 1000  # de miles a personas
ene_region = (
    ene_totales.groupby('Region_ES')['Ocupados'].mean()
    .reset_index()
    .rename(columns={'Region_ES': 'Región'})
)

df_cruce_region = pd.merge(acc_region, ene_region, on='Región', how='inner')
df_cruce_region['Tasa_Accidentabilidad_x_100k'] = (
    df_cruce_region['Accidentes'] / df_cruce_region['Ocupados'] * 100000
)
df_cruce_region['Participacion_%_Accidentes'] = (
    df_cruce_region['Accidentes'] / total_acc_nacional * 100
)

# Diagnóstico: regiones con accidentes pero sin denominador ENE
sin_denominador = acc_region[~acc_region['Región'].isin(df_cruce_region['Región'])]
if not sin_denominador.empty:
    print("\n[AVISO] Regiones excluidas por no tener ocupados en la ENE descargada:")
    for _, fila in sin_denominador.iterrows():
        print(f"   - {fila['Región']:<45} {fila['Accidentes']:>8,} accidentes "
              f"({fila['Accidentes'] / total_acc_nacional * 100:.1f}%)")

# ------------------------------------------------------------------
# 6. ANÁLISIS 2: TASA DE ACCIDENTABILIDAD POR SECTOR ECONÓMICO
#    Numerador  : SUM('Total') de accidentes 2024 por actividad (SUSESO)
#    Denominador: ocupados promedio 2024 por actividad (ENE, nivel nacional)
# ------------------------------------------------------------------
acc_sector = (
    df_acc_anio.groupby('Sector_ES')['Total'].sum()
    .reset_index()
    .rename(columns={'Total': 'Accidentes'})
)

ene_sector = df_ene[
    (df_ene['Region'] == 'Nationwide total')
    & (df_ene['Sex'] == 'Total')
    & (df_ene['Sector_ES'].notna())
].copy()
ene_sector['Ocupados'] = ene_sector['Value'] * 1000
ene_rama = ene_sector.groupby('Sector_ES')['Ocupados'].mean().reset_index()

df_cruce_sector = pd.merge(acc_sector, ene_rama, on='Sector_ES', how='inner')
df_cruce_sector['Tasa_Accidentabilidad_x_100k'] = (
    df_cruce_sector['Accidentes'] / df_cruce_sector['Ocupados'] * 100000
)
df_cruce_sector['Participacion_%_Accidentes'] = (
    df_cruce_sector['Accidentes'] / total_acc_nacional * 100
)

# Diagnóstico: sectores con accidentes pero sin denominador ENE
sin_denom_sector = acc_sector[~acc_sector['Sector_ES'].isin(df_cruce_sector['Sector_ES'])]
if not sin_denom_sector.empty:
    print("\n[AVISO] Sectores excluidos por no tener ocupados en la ENE:")
    for _, fila in sin_denom_sector.iterrows():
        print(f"   - {fila['Sector_ES']:<55} {fila['Accidentes']:>8,} accidentes")

# ------------------------------------------------------------------
# 7. GUARDAR RESULTADOS (ordenados por tasa, de mayor a menor)
# ------------------------------------------------------------------
resultado_region = (
    df_cruce_region[['Región', 'Accidentes', 'Participacion_%_Accidentes',
                     'Ocupados', 'Tasa_Accidentabilidad_x_100k']]
    .sort_values('Tasa_Accidentabilidad_x_100k', ascending=False)
    .copy()
)
resultado_region['Ocupados'] = resultado_region['Ocupados'].round(0)
resultado_region['Participacion_%_Accidentes'] = resultado_region['Participacion_%_Accidentes'].round(2)
resultado_region['Tasa_Accidentabilidad_x_100k'] = resultado_region['Tasa_Accidentabilidad_x_100k'].round(1)

resultado_sector = (
    df_cruce_sector[['Sector_ES', 'Accidentes', 'Participacion_%_Accidentes',
                     'Ocupados', 'Tasa_Accidentabilidad_x_100k']]
    .sort_values('Tasa_Accidentabilidad_x_100k', ascending=False)
    .copy()
)
resultado_sector['Ocupados'] = resultado_sector['Ocupados'].round(0)
resultado_sector['Participacion_%_Accidentes'] = resultado_sector['Participacion_%_Accidentes'].round(2)
resultado_sector['Tasa_Accidentabilidad_x_100k'] = resultado_sector['Tasa_Accidentabilidad_x_100k'].round(1)

ruta_salida_region = os.path.join('data', 'resultado_region.csv')
ruta_salida_sector = os.path.join('data', 'resultado_sector.csv')
resultado_region.to_csv(ruta_salida_region, index=False)
resultado_sector.to_csv(ruta_salida_sector, index=False)

print(f"\n=== PROCESO COMPLETADO EXITOSAMENTE (año {ANIO_ANALISIS}) ===")
print(f"1. Resultado Regional guardado en : {ruta_salida_region} ({len(resultado_region)} regiones)")
print(f"2. Resultado Sectorial guardado en: {ruta_salida_sector} ({len(resultado_sector)} sectores)")

print(f"\n--- Top 5 regiones (accidentes por 100.000 ocupados, {ANIO_ANALISIS}) ---")
print(resultado_region.head(5).to_string(index=False))
print(f"\n--- Top 5 sectores (accidentes por 100.000 ocupados, {ANIO_ANALISIS}) ---")
print(resultado_sector.head(5).to_string(index=False))





