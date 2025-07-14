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
Esta aplicación visualiza la serie histórica del **Dólar MEP** ajustada por la inflación de Argentina (IPC Nacional)
para reflejar su valor en pesos de hoy. Esto permite comparar el poder de compra real del dólar a lo largo del tiempo.
El círculo rojo destaca el comportamiento del precio desde la flexibilización cambiaria de mediados de abril de 2024.
""")

# --- FUNCIONES DE OBTENCIÓN DE DATOS (CON CACHÉ) ---

@st.cache_data(ttl=3600) # Cachea los datos por 1 hora
def get_historical_mep():
    """Obtiene el historial del Dólar MEP desde una API pública."""
    try:
        response = requests.get("https://dolarapi.com/v1/dolares/bolsa", timeout=10)
        response.raise_for_status() # Lanza un error si la petición falla
        data = response.json()
        df = pd.DataFrame(data)
        df = df[['fecha', 'venta']]
        df.columns = ['fecha', 'mep_nominal']
        df['fecha'] = pd.to_datetime(df['fecha'])
        return df.sort_values('fecha')
    except requests.RequestException as e:
        st.error(f"Error al obtener datos del Dólar MEP: {e}")
        return None

@st.cache_data(ttl=86400) # Cachea el IPC por 24 horas (cambia mensualmente)
def get_historical_ipc():
    """Obtiene el IPC Nacional GBA (base Dic 2016) desde la API del BCRA."""
    # El token de la API del BCRA es público
    token = "BEARER eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTI1MjQ5MDksInR5cGUiOiJleHRlcm5hbCIsInVzZXIiOiJqdWFuLmFtYWRvQGZpbml0ZWNoLmNvbS5hciJ9.7M0mS_kkONYrEp6Wpve0Y1c2-y1p2i-T9o_N2i_j2kzlq2iOa-Yd9iALV5IqLd_IpoCM_2Wv_z3e2hh-3Q7PXA"
    headers = {"Authorization": token}
    url = "https://api.bcra.gob.ar/estadisticas/v1/principalesvariables"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()['results']
        # ID 26 corresponde al IPC Nacional GBA, Nivel General, base Dic 2016
        ipc_data = next((item for item in data if item["idVariable"] == 26), None)
        if ipc_data:
            df = pd.DataFrame(ipc_data['principalesVariables'])
            df = df[['fecha', 'valor']]
            df.columns = ['fecha', 'ipc']
            df['fecha'] = pd.to_datetime(df['fecha'], format='%Y-%m-%d')
            # El IPC se publica a mes vencido, lo convertimos al primer día del mes para el cruce
            df['fecha'] = df['fecha'].dt.to_period('M').dt.to_timestamp()
            # Aseguramos que el valor del IPC es numérico
            df['ipc'] = pd.to_numeric(df['ipc'])
            return df.sort_values('fecha')
        else:
            st.error("No se encontró la variable IPC (ID 26) en la respuesta del BCRA.")
            return None
            
    except requests.RequestException as e:
        st.error(f"Error al obtener datos del IPC desde el BCRA: {e}")
        return None
    except (KeyError, IndexError):
        st.error("La estructura de datos del BCRA ha cambiado. No se pudo procesar el IPC.")
        return None

# --- LÓGICA PRINCIPAL DE LA APLICACIÓN ---
with st.spinner("Cargando y procesando datos históricos..."):
    df_mep = get_historical_mep()
    df_ipc = get_historical_ipc()

    if df_mep is not None and df_ipc is not None and not df_mep.empty and not df_ipc.empty:
        # 1. Unir los dos DataFrames.
        # `merge_asof` es ideal para esto: para cada día en `df_mep`,
        # busca el último valor de IPC disponible en `df_ipc`.
        df_merged = pd.merge_asof(
            df_mep.sort_values('fecha'),
            df_ipc.sort_values('fecha'),
            on='fecha',
            direction='backward' # Usa el último IPC conocido para una fecha dada
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
            line=dict(color='#00BFFF', width=2), # Azul cian
             hoverinfo='text',
             hovertext=[
                 f"<b>Fecha:</b> {row.fecha.strftime('%d-%m-%Y')}<br>"
                 f"<b>MEP Ajustado:</b> ${row.mep_ajustado:,.2f}<br>"
                 f"<b>MEP Nominal:</b> ${row.mep_nominal:,.2f}"
                 for row in df_merged.itertuples()
             ]
        ))
        
        # 4. Añadir el círculo rojo de la imagen de ejemplo
        # Definimos el rango a destacar
        highlight_start_date = datetime(2024, 4, 15)
        df_highlight = df_merged[df_merged['fecha'] >= highlight_start_date]

        if not df_highlight.empty:
            # Encontrar los límites para dibujar una forma de elipse/círculo
            x0 = df_highlight['fecha'].min()
            x1 = df_highlight['fecha'].max() + pd.Timedelta(days=10) # Un poco más de espacio
            y0 = df_highlight['mep_ajustado'].min() * 0.95
            y1 = df_highlight['mep_ajustado'].max() * 1.05

            fig.add_shape(
                type="rect", # 'rect' es más robusto para este tipo de highlight
                xref="x", yref="y",
                x0=x0, y0=y0, x1=x1, y1=y1,
                line=dict(color="Crimson", width=2, dash="dot"),
                fillcolor="rgba(220, 20, 60, 0.1)" # Relleno semi-transparente
            )

        # 5. Configurar el layout del gráfico
        fig.update_layout(
            template='plotly_dark',
            title='<b>Dólar MEP a Precios de Hoy (Ajustado por IPC)</b>',
            yaxis_title='Valor en Pesos Argentinos (de hoy)',
            xaxis_title='Fecha',
            height=600,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(
                tickprefix="$",
                tickformat=",.0f"
            )
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar una nota sobre el último dato de IPC utilizado
        st.info(
            f"📈 Último dato de IPC utilizado para el ajuste corresponde a **{fecha_ultimo_ipc.strftime('%B de %Y')}** (valor: {ipc_actual}). "
            f"Los precios posteriores a esa fecha se ajustan con este último valor.",
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
st.caption("Fuente de Datos: Dólar MEP de [dolarapi.com](https://dolarapi.com/) | IPC Nacional GBA desde [api.bcra.gob.ar](https://www.bcra.gob.ar/BCRAyVos/p-API-BCRA.asp).")
