import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dólar MEP a Precios de Hoy",
    page_icon="🇦🇷",
    layout="wide"
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("📈 Dólar MEP Histórico a Precios de Hoy")
st.markdown("""
Esta aplicación visualiza la serie histórica del **Dólar MEP (implícito)**, ajustada por la inflación de Argentina (IPC Nacional),
para reflejar su valor en pesos de hoy. El cálculo se basa en la cotización de los bonos soberanos **AL30** y **AL30D**.
El área destacada en rojo muestra el comportamiento del precio desde mediados de abril de 2024.
""")

# --- FUNCIONES DE OBTENCIÓN DE DATOS (CON CACHÉ) ---

@st.cache_data(ttl=3600) # Cachea los datos por 1 hora
def get_mep_from_data912():
    """
    Calcula el Dólar MEP implícito usando los datos históricos de los bonos
    AL30 y AL30D desde la API de data912.com.
    """
    try:
        # 1. Obtener datos del bono AL30 en Pesos
        url_ars = "https://data912.com/historical/bonds/AL30"
        response_ars = requests.get(url_ars, timeout=20)
        response_ars.raise_for_status()
        data_ars = response_ars.json()
        df_ars = pd.DataFrame(data_ars)
        # Seleccionamos fecha y precio de cierre ('c')
        df_ars = df_ars[['date', 'c']].rename(columns={'date': 'fecha', 'c': 'al30_ars'})
        df_ars['fecha'] = pd.to_datetime(df_ars['fecha'])

        # 2. Obtener datos del bono AL30D en Dólares
        url_usd = "https://data912.com/historical/bonds/AL30D"
        response_usd = requests.get(url_usd, timeout=20)
        response_usd.raise_for_status()
        data_usd = response_usd.json()
        df_usd = pd.DataFrame(data_usd)
        df_usd = df_usd[['date', 'c']].rename(columns={'date': 'fecha', 'c': 'al30_usd'})
        df_usd['fecha'] = pd.to_datetime(df_usd['fecha'])

        # 3. Unir los DataFrames por fecha
        df = pd.merge(df_ars, df_usd, on='fecha')
        df.dropna(inplace=True)

        # 4. Calcular MEP: Precio en ARS / Precio en USD
        df['mep_nominal'] = df['al30_ars'] / df['al30_usd']
        
        # 5. Devolver el DataFrame final con el formato esperado
        df_mep = df[['fecha', 'mep_nominal']]
        
        # Filtro simple para valores atípicos
        return df_mep[df_mep['mep_nominal'] > 0]

    except requests.RequestException as e:
        st.error(f"Error al conectar con la API de data912.com: {e}")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error al procesar los datos de los bonos: {e}")
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
    df_mep = get_mep_from_data912()
    df_ipc = get_ipc_from_datos_gob_ar()

    if df_mep is not None and df_ipc is not None and not df_mep.empty and not df_ipc.empty:
        # 1. Unir los dos DataFrames.
        df_merged = pd.merge_asof(
            df_mep.sort_values('fecha'),
            df_ipc.sort_values('fecha'),
            on='fecha',
            direction='backward'
        )
        df_merged.dropna(inplace=True)

        # 2. Calcular el MEP ajustado a precios de hoy
        ipc_actual = df_merged['ipc'].iloc[-1]
        fecha_ultimo_ipc = df_ipc['fecha'].iloc[-1]
        
        df_merged['mep_ajustado'] = df_merged['mep_nominal'] * (ipc_actual / df_merged['ipc'])

        # 3. Crear el gráfico con Plotly
        fig = go.Figure()

        # Línea principal del MEP ajustado
        fig.add_trace(go.Scatter(
            x=df_merged['fecha'],
            y=df_merged['mep_ajustado'],
            mode='lines',
            name='Dólar MEP ajustado',
            line=dict(color='#00BFFF', width=2.5),
            hoverinfo='text',
            hovertext=[
                f"<b>Fecha:</b> {row.fecha.strftime('%d-%m-%Y')}<br>"
                f"<b>MEP Ajustado:</b> ${row.mep_ajustado:,.2f}<br>"
                f"<b>MEP Nominal:</b> ${row.mep_nominal:,.2f}"
                for row in df_merged.itertuples()
            ]
        ))
        
        # 4. Añadir el área destacada
        highlight_start_date = datetime(2024, 4, 15)
        df_highlight = df_merged[df_merged['fecha'] >= highlight_start_date]

        if not df_highlight.empty:
            fig.add_trace(go.Scatter(
                x=df_highlight['fecha'],
                y=df_highlight['mep_ajustado'],
                fill='tozeroy',
                mode='none',
                fillcolor='rgba(220, 20, 60, 0.2)',
                name='Período Reciente',
                hoverinfo='none'
            ))

        # 5. Configurar el layout del gráfico
        fig.update_layout(
            template='plotly_dark',
            title='<b>Dólar MEP a Precios de Hoy (Ajustado por IPC)</b>',
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
                df_merged[['fecha', 'mep_nominal', 'ipc', 'mep_ajustado']].style.format({
                    'mep_nominal': '${:,.2f}',
                    'ipc': '{:.2f}',
                    'mep_ajustado': '${:,.2f}',
                    'fecha': '{:%d-%m-%Y}'
                }),
                use_container_width=True
            )

    else:
        st.error("No se pudieron cargar todos los datos necesarios para generar el gráfico. Por favor, intente de nuevo más tarde.")

st.markdown("---")
st.caption("Fuente de Datos: MEP implícito calculado con bonos AL30/AL30D desde data912.com | IPC Nacional desde datos.gob.ar.")
