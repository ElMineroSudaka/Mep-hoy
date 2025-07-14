import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
import yfinance as yf
import time # Importar la librería time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dólar Financiero a Precios de Hoy",
    page_icon="🇦�",
    layout="wide"
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("📈 Dólar Financiero (CCL) Histórico a Precios de Hoy")
st.markdown("""
Esta aplicación visualiza la serie histórica del **Dólar Contado con Liquidación (implícito)**, ajustada por la inflación de Argentina (IPC Nacional),
para reflejar su valor en pesos de hoy. El cálculo se basa en la cotización de las acciones de **Grupo Financiero Galicia (GGAL)**.
El área destacada en rojo muestra el comportamiento del precio desde mediados de abril de 2024.
""")

# --- FUNCIONES DE OBTENCIÓN DE DATOS (CON CACHÉ) ---

@st.cache_data(ttl=3600) # Cachea los datos por 1 hora
def get_ccl_from_ggal(start_date="2015-01-01"):
    """
    Calcula el Dólar CCL implícito siguiendo una lógica específica:
    1. Obtiene el precio en USD (ADR) desde Yahoo Finance (crítico).
    2. Intenta obtener el precio en ARS desde Yahoo Finance.
    3. Si el paso 2 falla, usa data912.com como respaldo para el precio en ARS.
    """
    df_ars = None
    df_usd = None

    # Paso 1: Obtener GGAL ADR en USD (fuente única y crítica)
    try:
        st.info("Obteniendo precio en Dólares (GGAL ADR) desde Yahoo Finance...")
        ggal_adr = yf.download("GGAL", start=start_date, progress=False, auto_adjust=True)
        if ggal_adr.empty:
            raise ValueError("No se pudieron obtener los datos del ADR (GGAL) desde Yahoo Finance.")
        # CORRECCIÓN: Asegurar que los datos son 1D antes de crear el DataFrame
        df_usd = pd.DataFrame({'fecha': ggal_adr.index, 'ggal_usd': ggal_adr['Close'].values})
        st.success("Precio en Dólares obtenido exitosamente.")
    except Exception as e_adr:
        st.error(f"Error crítico: No se pudo obtener el precio en Dólares desde Yahoo Finance. {e_adr}")
        return None

    # Paso 2: Intentar obtener GGAL en ARS desde Yahoo Finance
    try:
        st.info("Intentando obtener precio en Pesos (GGAL.BA) desde Yahoo Finance...")
        ggal_ba = yf.download("GGAL.BA", start=start_date, progress=False, auto_adjust=True)
        if ggal_ba.empty:
            raise ValueError("yf.download() para GGAL.BA devolvió un DataFrame vacío.")
        # CORRECCIÓN: Asegurar que los datos son 1D antes de crear el DataFrame
        df_ars = pd.DataFrame({'fecha': ggal_ba.index, 'ggal_ars': ggal_ba['Close'].values})
        st.success("Precio en Pesos obtenido desde Yahoo Finance.")
    except Exception as e_yf_ba:
        st.warning(f"Falló la obtención de GGAL.BA desde Yahoo Finance: {e_yf_ba}. Usando respaldo...")
        # Paso 3: Fallback para el precio en ARS desde data912.com
        try:
            url_ars = "https://data912.com/historical/stocks/ggal"
            response_ars = requests.get(url_ars, timeout=20)
            response_ars.raise_for_status()
            data_ars = response_ars.json()
            df_ars_fallback = pd.DataFrame(data_ars)
            df_ars = df_ars_fallback[['date', 'c']].rename(columns={'date': 'fecha', 'c': 'ggal_ars'})
            df_ars['fecha'] = pd.to_datetime(df_ars['fecha'])
            st.success("Precio en Pesos obtenido desde la fuente de respaldo (data912.com).")
        except Exception as e_fallback:
            st.error(f"Falló también la fuente de respaldo para el precio en Pesos: {e_fallback}")
            return None

    # Paso 4: Unir los DataFrames y calcular
    if df_ars is not None and df_usd is not None:
        df = pd.merge(df_ars, df_usd, on='fecha')
        df.dropna(inplace=True)
        df['ccl_nominal'] = (df['ggal_ars'].squeeze() / df['ggal_usd'].squeeze()) * 10
        df_ccl = df[['fecha', 'ccl_nominal']]
        return df_ccl[df_ccl['ccl_nominal'] > 0]
    else:
        st.error("No se pudieron consolidar los datos de precios en ARS y USD.")
        return None


@st.cache_data(ttl=86400) # Cachea el IPC por 24 horas
def get_ipc_from_datos_gob_ar():
    """
    Obtiene el IPC Nacional (base Dic 2016) desde la API de datos.gob.ar.
    ID de la serie: 148.3_INIVELNAL_DICI_M_26
    """
    url = "https://apis.datos.gob.ar/series/api/series/?ids=148.3_INIVELNAL_DICI_M_26"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()['data']
        
        df = pd.DataFrame(data, columns=['fecha', 'ipc'])
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['ipc'] = pd.to_numeric(df['ipc'])
        
        df['fecha'] = df['fecha'].dt.to_period('M').dt.to_timestamp()
        return df.sort_values('fecha')

    except requests.RequestException as e:
        st.error(f"Error al conectar con la API de datos.gob.ar: {e}")
        return None
    except (KeyError, IndexError):
        st.error("La estructura de datos de la API de IPC ha cambiado.")
        return None

# --- LÓGICA PRINCIPAL DE LA APLICACIÓN ---
with st.spinner("Cargando y procesando datos... (puede tardar un momento la primera vez)"):
    df_ccl = get_ccl_from_ggal()
    df_ipc = get_ipc_from_datos_gob_ar()

    if df_ccl is not None and df_ipc is not None and not df_ccl.empty and not df_ipc.empty:
        # 1. Unir los dos DataFrames.
        df_merged = pd.merge_asof(
            df_ccl.sort_values('fecha'),
            df_ipc.sort_values('fecha'),
            on='fecha',
            direction='backward'
        )
        df_merged.dropna(inplace=True)

        # 2. Calcular el CCL ajustado a precios de hoy
        ipc_actual = df_merged['ipc'].iloc[-1]
        fecha_ultimo_ipc = df_ipc['fecha'].iloc[-1]
        
        df_merged['ccl_ajustado'] = df_merged['ccl_nominal'] * (ipc_actual / df_merged['ipc'])

        # 3. Crear el gráfico con Plotly
        fig = go.Figure()

        # Línea principal del CCL ajustado
        fig.add_trace(go.Scatter(
            x=df_merged['fecha'],
            y=df_merged['ccl_ajustado'],
            mode='lines',
            name='Dólar CCL ajustado',
            line=dict(color='#00BFFF', width=2.5),
            hoverinfo='text',
            hovertext=[
                f"<b>Fecha:</b> {row.fecha.strftime('%d-%m-%Y')}<br>"
                f"<b>CCL Ajustado:</b> ${row.ccl_ajustado:,.2f}<br>"
                f"<b>CCL Nominal:</b> ${row.ccl_nominal:,.2f}"
                for row in df_merged.itertuples()
            ]
        ))
        
        # 4. Añadir el área destacada
        highlight_start_date = datetime(2024, 4, 15)
        df_highlight = df_merged[df_merged['fecha'] >= highlight_start_date]

        if not df_highlight.empty:
            fig.add_trace(go.Scatter(
                x=df_highlight['fecha'],
                y=df_highlight['ccl_ajustado'],
                fill='tozeroy',
                mode='none',
                fillcolor='rgba(220, 20, 60, 0.2)',
                name='Período Reciente',
                hoverinfo='none'
            ))

        # 5. Configurar el layout del gráfico
        fig.update_layout(
            template='plotly_dark',
            title='<b>Dólar CCL a Precios de Hoy (Ajustado por IPC)</b>',
            yaxis_title='Valor en Pesos Argentinos (de hoy)',
            xaxis_title='Fecha',
            height=600,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(tickprefix="$", tickformat=",.0f")
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar una nota sobre el último dato de IPC utilizado
        st.info(
            f"📈 Último dato de IPC utilizado para el ajuste corresponde a **{fecha_ultimo_ipc.strftime('%B de %Y')}**. "
            f"Los precios posteriores se ajustan con este último valor disponible.",
            icon="ℹ️"
        )
        
        # Expansor para mostrar los datos en una tabla
        with st.expander("Ver tabla de datos completos"):
            st.dataframe(
                df_merged[['fecha', 'ccl_nominal', 'ipc', 'ccl_ajustado']].style.format({
                    'ccl_nominal': '${:,.2f}',
                    'ipc': '{:.2f}',
                    'ccl_ajustado': '${:,.2f}',
                    'fecha': '{:%d-%m-%Y}'
                }),
                use_container_width=True
            )

    else:
        st.error("No se pudieron cargar todos los datos necesarios para generar el gráfico. Por favor, intente de nuevo más tarde.")

st.markdown("---")
st.caption("Fuente de Datos: CCL implícito calculado con GGAL/GGAL.BA (con respaldo de data912.com) | IPC Nacional desde datos.gob.ar.")
