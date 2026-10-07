from pathlib import Path
import subprocess
import sys

import altair as alt
import pandas as pd
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
SCRIPT_PATH = PROJECT_DIR / "tratado.py"
REGION_PATH = DATA_DIR / "resultado_region.csv"
SECTOR_PATH = DATA_DIR / "resultado_sector.csv"
SOURCE_PATHS = (
    DATA_DIR / "accidentes_trabajo_trayecto_datos_gob.csv",
    DATA_DIR / "ENE_OCU_RAMA_06102026154800949.csv",
)
RATE_COLUMN = "Tasa_Accidentabilidad_x_100k"
ACCIDENT_COLUMN = "Accidentes"

st.set_page_config(
    page_title="Accidentabilidad laboral | Chile",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        [data-testid="stMetric"] {
            background: #f4f7fb;
            border: 1px solid #e5eaf1;
            padding: 1rem 1.2rem;
            border-radius: 12px;
        }
        h1, h2, h3 { letter-spacing: -0.03em; }
    </style>
    """,
    unsafe_allow_html=True,
)


def ensure_results():
    """Generate the analysis outputs when they're missing or out of date."""
    missing_sources = [path.name for path in SOURCE_PATHS if not path.exists()]
    if missing_sources:
        raise FileNotFoundError(
            "No se encontraron los archivos fuente en data/: "
            + ", ".join(missing_sources)
        )

    outputs = (REGION_PATH, SECTOR_PATH)
    needs_refresh = any(
        not output.exists()
        or any(source.stat().st_mtime > output.stat().st_mtime for source in SOURCE_PATHS)
        or SCRIPT_PATH.stat().st_mtime > output.stat().st_mtime
        for output in outputs
    )
    if needs_refresh:
        subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )


@st.cache_data(show_spinner=False)
def load_results():
    ensure_results()
    regions = pd.read_csv(REGION_PATH)
    sectors = pd.read_csv(SECTOR_PATH)
    required_columns = {
        "region": {"Región", ACCIDENT_COLUMN, RATE_COLUMN, "Ocupados", "Participacion_%_Accidentes"},
        "sector": {"Sector_ES", ACCIDENT_COLUMN, RATE_COLUMN, "Ocupados", "Participacion_%_Accidentes"},
    }
    for label, frame, columns in (
        ("regional", regions, required_columns["region"]),
        ("sectorial", sectors, required_columns["sector"]),
    ):
        missing = columns.difference(frame.columns)
        if missing:
            raise ValueError(
                f"El resultado {label} no tiene las columnas esperadas: "
                + ", ".join(sorted(missing))
            )
    return regions, sectors


def number(value, decimals=0):
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def make_chart(data, label_column, metric_column, title, color, height):
    chart_data = data[[label_column, metric_column]].copy()
    chart_data[metric_column] = pd.to_numeric(chart_data[metric_column], errors="coerce")
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusEnd=4, color=color)
        .encode(
            x=alt.X(f"{metric_column}:Q", title=title, axis=alt.Axis(format=",.0f")),
            y=alt.Y(
                f"{label_column}:N",
                title=None,
                sort=alt.SortField(field=metric_column, order="descending"),
                axis=alt.Axis(labelLimit=320),
            ),
            tooltip=[
                alt.Tooltip(f"{label_column}:N", title="Categoría"),
                alt.Tooltip(f"{metric_column}:Q", title=title, format=",.1f"),
            ],
        )
        .properties(height=height)
        .configure_view(strokeOpacity=0)
        .configure_axis(gridColor="#e9edf3", domain=False, tickColor="#e9edf3")
    )


def show_table(frame, category_column):
    display = frame.rename(
        columns={
            category_column: "Categoría",
            ACCIDENT_COLUMN: "Accidentes",
            "Participacion_%_Accidentes": "Participación nacional (%)",
            "Ocupados": "Personas ocupadas",
            RATE_COLUMN: "Accidentes por 100.000 ocupados",
        }
    ).copy()
    display["Accidentes"] = display["Accidentes"].map(lambda value: number(value))
    display["Participación nacional (%)"] = display[
        "Participación nacional (%)"
    ].map(lambda value: f"{number(value, 2)}%")
    display["Personas ocupadas"] = display["Personas ocupadas"].map(
        lambda value: number(value)
    )
    display["Accidentes por 100.000 ocupados"] = display[
        "Accidentes por 100.000 ocupados"
    ].map(lambda value: number(value, 1))
    st.dataframe(display, hide_index=True, use_container_width=True)


st.title("Accidentabilidad laboral en Chile")
st.caption(
    "Accidentes del trabajo y de trayecto (SUSESO) en relación con la población "
    "ocupada (INE-ENE) · Año 2024"
)

try:
    with st.spinner("Preparando los resultados del análisis..."):
        region_data, sector_data = load_results()
except (FileNotFoundError, ValueError, subprocess.CalledProcessError, OSError) as error:
    st.error(f"No fue posible cargar los resultados: {error}")
    if isinstance(error, subprocess.CalledProcessError):
        with st.expander("Ver salida del proceso de análisis"):
            if error.stdout:
                st.text(error.stdout)
            if error.stderr:
                st.text(error.stderr)
    st.stop()

top_region = region_data.loc[region_data[RATE_COLUMN].idxmax()]
top_sector = sector_data.loc[sector_data[RATE_COLUMN].idxmax()]
analysed_accidents = region_data[ACCIDENT_COLUMN].sum()

metric_columns = st.columns(4)
metric_columns[0].metric("Accidentes en regiones analizadas", number(analysed_accidents))
metric_columns[1].metric("Regiones con datos comparables", number(len(region_data)))
metric_columns[2].metric("Mayor tasa regional", f"{number(top_region[RATE_COLUMN], 1)}")
metric_columns[3].metric("Mayor tasa sectorial", f"{number(top_sector[RATE_COLUMN], 1)}")

st.caption(
    "La tasa expresa accidentes registrados por cada 100.000 personas ocupadas. "
    "El denominador ENE corresponde al promedio de cuatro trimestres móviles de 2024."
)

overview_tab, regions_tab, sectors_tab = st.tabs(
    ["Resumen", "Por región", "Por sector económico"]
)

with overview_tab:
    left, right = st.columns(2)
    with left:
        st.subheader("Tasa por región")
        st.altair_chart(
            make_chart(
                region_data.nlargest(8, RATE_COLUMN),
                "Región",
                RATE_COLUMN,
                "Accidentes por 100.000 ocupados",
                "#2563eb",
                340,
            ),
            use_container_width=True,
        )
    with right:
        st.subheader("Tasa por sector")
        st.altair_chart(
            make_chart(
                sector_data.nlargest(8, RATE_COLUMN),
                "Sector_ES",
                RATE_COLUMN,
                "Accidentes por 100.000 ocupados",
                "#0f766e",
                340,
            ),
            use_container_width=True,
        )
    st.info(
        "La cobertura regional de la ENE descargada no incluye Los Lagos, Aysén ni "
        "Magallanes. Sus accidentes no aparecen en la comparación regional."
    )

with regions_tab:
    st.subheader("Comparación regional")
    region_metric = st.radio(
        "Métrica",
        ["Tasa por 100.000 ocupados", "Número de accidentes"],
        horizontal=True,
        key="region_metric",
    )
    region_column = RATE_COLUMN if region_metric.startswith("Tasa") else ACCIDENT_COLUMN
    region_label = (
        "Accidentes por 100.000 ocupados"
        if region_column == RATE_COLUMN
        else "Accidentes registrados"
    )
    region_count = st.slider(
        "Regiones mostradas", min_value=5, max_value=len(region_data), value=len(region_data)
    )
    region_view = region_data.nlargest(region_count, region_column)
    st.altair_chart(
        make_chart(
            region_view,
            "Región",
            region_column,
            region_label,
            "#2563eb",
            max(280, region_count * 30),
        ),
        use_container_width=True,
    )
    show_table(region_view, "Región")

with sectors_tab:
    st.subheader("Comparación por actividad económica")
    sector_metric = st.radio(
        "Métrica",
        ["Tasa por 100.000 ocupados", "Número de accidentes"],
        horizontal=True,
        key="sector_metric",
    )
    sector_column = RATE_COLUMN if sector_metric.startswith("Tasa") else ACCIDENT_COLUMN
    sector_label = (
        "Accidentes por 100.000 ocupados"
        if sector_column == RATE_COLUMN
        else "Accidentes registrados"
    )
    sector_count = st.slider(
        "Sectores mostrados",
        min_value=5,
        max_value=len(sector_data),
        value=len(sector_data),
    )
    sector_view = sector_data.nlargest(sector_count, sector_column)
    st.altair_chart(
        make_chart(
            sector_view,
            "Sector_ES",
            sector_column,
            sector_label,
            "#0f766e",
            max(280, sector_count * 34),
        ),
        use_container_width=True,
    )
    show_table(sector_view, "Sector_ES")
    st.warning(
        "La tasa del sector «Actividades inmobiliarias, empresariales y de alquiler» "
        "incluye servicios empresariales y de personal transitorio; no representa "
        "solo actividades inmobiliarias."
    )

st.divider()
st.caption(
    "Fuentes: SUSESO, datos.gob.cl · INE, Encuesta Nacional de Empleo. "
    "Las categorías económicas se homologaron entre CIIU 2007 y CAENES 2.0."
)
