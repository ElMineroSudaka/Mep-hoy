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
Esta aplicación visualiza la serie histórica del **Dólar MEP (implícito)** ajustada por la inflación de Argentina (IPC Nacional)
para reflejar su valor en pesos de hoy. Esto permite comparar el poder de compra real del dólar a lo largo del tiempo.
El área destacada en rojo muestra el comportamiento del precio desde mediados de abril de 2024.
""")

# --- FUNCIONES DE OBTENCIÓN DE DATOS (CON CACHÉ) ---

# Token público y headers para la API del BCRA
BCRA_API_TOKEN = "BEARER eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTI1MjQ5MDksInR5cGUiOiJleHRlcm5hbCIsInVzZXIiOiJqdWFuLmFtYWRvQGZpbml0ZWNoLmNvbS5hciJ9.7M0mS_kkONYrEp6Wpve0Y1c2-y1p2i-T9o_N2i_j2kzlq2iOa-Yd9iALV5IqLd_IpoCM_2Wv_z3e2hh-3Q7PXA"
BCRA_HEADERS = {"Authorization": BCRA_API_TOKEN}

@st.cache_data(ttl=3600) # Cachea los datos por 1 hora
def get_bcra_series(variable_id, column_name):
    """
    Función genérica para obtener una serie de tiempo de la API del BCRA.
    
    Args:
        variable_id (int): El ID de la variable a consultar.
        column_name (str): El nombre a asignar a la columna de valor.

    Returns:
        pd.DataFrame: Un DataFrame con 'fecha' y la columna de valor especificada.
    """
    url = "https://api.bcra.gob.ar/estadisticas/v1/principalesvariables"
    try:
        response = requests.get(url, headers=BCRA_HEADERS, timeout=20)
        response.raise_for_status()
        all_data = response.json()['results']
        
        series_data = next((item for item in all_data if item["idVariable"] == variable_id), None)
        
        if series_data and series_data.get('principalesVariables'):
            df = pd.DataFrame(series_data['principalesVariables'])
            df = df[['fecha', 'valor']]
            df.columns = ['fecha', column_name]
            df['fecha'] = pd.to_datetime(df['fecha'], format='%Y-%m-%d')
            df[column_name] = pd.to_numeric(df[column_name].astype(str).str.replace(',', '.'))
            df = df[df[column_name] > 0].dropna() # Filtrar valores nulos o incorrectos
            return df.sort_values('fecha')
        else:
            st.error(f"No se encontraron datos para la variable con ID {variable_id} en la respuesta del BCRA.")
            return None
            
    except requests.RequestException as e:
        st.error(f"Error al conectar con la API del BCRA: {e}")
        return None
    except (KeyError, IndexError):
        st.error("La estructura de datos del BCRA parece haber cambiado. No se pudo procesar la solicitud.")
        return None

# --- LÓGICA PRINCIPAL DE LA APLICACIÓN ---
with st.spinner("Cargando y procesando datos históricos desde el BCRA..."):
    # ID 296: Tipo de cambio implícito en bonos soberanos (diaria) -> Proxy MEP
    # ID 26: IPC Nacional GBA, Nivel General, base Dic 2016
    df_mep = get_bcra_series(variable_id=296, column_name='mep_nominal')
    df_ipc = get_bcra_series(variable_id=26, column_name='ipc')
    
    # El IPC se publica mensualmente, lo preparamos para el cruce
    if df_ipc is not None:
        df_ipc['fecha'] = df_ipc['fecha'].dt.to_period('M').dt.to_timestamp()


    if df_mep is not None and df_ipc is not None and not df_mep.empty and not df_ipc.empty:
        # 1. Unir los dos DataFrames.
        df_merged = pd.merge_asof(
            df_mep,
            df_ipc,
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
        st.error("No se pudieron cargar todos los datos necesarios desde el BCRA para generar el gráfico. Por favor, intente de nuevo más tarde.")

st.markdown("---")
st.caption("Fuente de Datos: Tipo de Cambio Implícito e IPC Nacional GBA desde la API de Estadísticas del [Banco Central de la República Argentina (BCRA)](https://www.bcra.gob.ar/BCRAyVos/p-API-BCRA.asp).")
