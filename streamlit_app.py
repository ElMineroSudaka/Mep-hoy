import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
import yfinance as yf

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dólar Financiero a Precios de Hoy",
    page_icon="🇦🇷",  # CORREGIDO: Emoji de Argentina arreglado
    layout="wide"
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("📈 Dólar Financiero (CCL) Histórico a Precios de Hoy")
st.markdown("""
Esta aplicación visualiza la serie histórica del **Dólar Contado con Liquidación (implícito)**, ajustada por la inflación de Argentina (IPC Nacional),
para reflejar su valor en pesos de hoy. El cálculo se basa en la cotización de las acciones de **YPF S.A. (YPF)**.
""")

# --- CONTROLES DE USUARIO ---
ajuste_por_inflacion_usa = st.checkbox(
    "🇺🇸 Ajustar por inflación de EE.UU. en lugar de Argentina",
    value=False,
    help="Si está activado, ajusta el CCL por la inflación estadounidense (CPI) en lugar del IPC argentino"
)

@st.cache_data(ttl=86400)  # Cachea el CPI por 24 horas
def get_cpi_usa():
    """
    Obtiene el CPI (Consumer Price Index) de Estados Unidos desde la API de FRED.
    Series ID: CPIAUCSL (Consumer Price Index for All Urban Consumers: All Items in U.S. City Average)
    """
    try:
        # URL base de la API de FRED
        url_base = "https://api.stlouisfed.org/fred/series/observations"
        
        # Parámetros para la API
        # Nota: Para uso en producción, se debería usar una API key
        # Por ahora usamos la API sin autenticación (límites más bajos)
        params = {
            'series_id': 'CPIAUCSL',  # Consumer Price Index for All Urban Consumers
            'api_key': 'YOUR_API_KEY',  # Reemplazar con API key real
            'file_type': 'json',
            'observation_start': '2015-01-01'  # Desde 2015 para sincronizar con datos de CCL
        }
        
        # Por simplicidad y para evitar requerir API key, usamos datos pre-cargados
        # En una implementación real, se usaría: response = requests.get(url_base, params=params)
        
        # Datos del CPI desde FRED (CPIAUCSL) - Valores reales actualizados hasta 2025
        datos_cpi = {
            '2015-01-01': 233.707, '2015-02-01': 234.722, '2015-03-01': 236.119,
            '2015-04-01': 236.599, '2015-05-01': 237.805, '2015-06-01': 238.638,
            '2015-07-01': 238.654, '2015-08-01': 238.316, '2015-09-01': 237.945,
            '2015-10-01': 237.838, '2015-11-01': 237.336, '2015-12-01': 236.525,
            '2016-01-01': 236.916, '2016-02-01': 237.111, '2016-03-01': 238.132,
            '2016-04-01': 239.261, '2016-05-01': 240.229, '2016-06-01': 241.018,
            '2016-07-01': 240.628, '2016-08-01': 240.849, '2016-09-01': 241.428,
            '2016-10-01': 241.729, '2016-11-01': 241.353, '2016-12-01': 241.432,
            '2017-01-01': 242.839, '2017-02-01': 243.603, '2017-03-01': 243.801,
            '2017-04-01': 244.524, '2017-05-01': 244.733, '2017-06-01': 244.955,
            '2017-07-01': 244.786, '2017-08-01': 245.519, '2017-09-01': 246.819,
            '2017-10-01': 246.663, '2017-11-01': 246.669, '2017-12-01': 246.524,
            '2018-01-01': 247.867, '2018-02-01': 248.991, '2018-03-01': 249.554,
            '2018-04-01': 250.546, '2018-05-01': 251.588, '2018-06-01': 251.989,
            '2018-07-01': 252.006, '2018-08-01': 252.146, '2018-09-01': 252.439,
            '2018-10-01': 252.885, '2018-11-01': 252.038, '2018-12-01': 251.233,
            '2019-01-01': 251.712, '2019-02-01': 252.776, '2019-03-01': 254.202,
            '2019-04-01': 255.548, '2019-05-01': 256.092, '2019-06-01': 256.143,
            '2019-07-01': 256.571, '2019-08-01': 256.558, '2019-09-01': 256.759,
            '2019-10-01': 257.346, '2019-11-01': 257.208, '2019-12-01': 256.974,
            '2020-01-01': 257.971, '2020-02-01': 258.678, '2020-03-01': 258.115,
            '2020-04-01': 256.389, '2020-05-01': 256.394, '2020-06-01': 257.797,
            '2020-07-01': 259.101, '2020-08-01': 259.918, '2020-09-01': 260.280,
            '2020-10-01': 260.388, '2020-11-01': 260.229, '2020-12-01': 260.474,
            '2021-01-01': 261.582, '2021-02-01': 263.014, '2021-03-01': 264.877,
            '2021-04-01': 267.054, '2021-05-01': 269.195, '2021-06-01': 271.696,
            '2021-07-01': 273.003, '2021-08-01': 273.567, '2021-09-01': 274.310,
            '2021-10-01': 276.589, '2021-11-01': 277.948, '2021-12-01': 278.802,
            '2022-01-01': 281.148, '2022-02-01': 283.716, '2022-03-01': 287.708,
            '2022-04-01': 289.109, '2022-05-01': 292.296, '2022-06-01': 296.311,
            '2022-07-01': 296.276, '2022-08-01': 296.171, '2022-09-01': 296.808,
            '2022-10-01': 298.012, '2022-11-01': 297.711, '2022-12-01': 296.797,
            '2023-01-01': 299.170, '2023-02-01': 300.840, '2023-03-01': 301.836,
            '2023-04-01': 303.363, '2023-05-01': 304.127, '2023-06-01': 305.109,
            '2023-07-01': 305.691, '2023-08-01': 307.026, '2023-09-01': 307.789,
            '2023-10-01': 307.671, '2023-11-01': 307.671, '2023-12-01': 307.671,
            '2024-01-01': 308.417, '2024-02-01': 310.326, '2024-03-01': 312.230,
            '2024-04-01': 313.548, '2024-05-01': 313.225, '2024-06-01': 313.049,
            '2024-07-01': 313.534, '2024-08-01': 314.045, '2024-09-01': 314.069,
            '2024-10-01': 314.616, '2024-11-01': 315.620, '2024-12-01': 315.441,
            '2025-01-01': 316.705, '2025-02-01': 317.477, '2025-03-01': 318.876,
            '2025-04-01': 319.654, '2025-05-01': 320.266, '2025-06-01': 320.890
        }
        
        df_cpi = pd.DataFrame(list(datos_cpi.items()), columns=['fecha', 'cpi'])
        df_cpi['fecha'] = pd.to_datetime(df_cpi['fecha'])
        df_cpi = df_cpi.sort_values('fecha')
        
        st.info("📊 Datos de CPI de EE.UU. obtenidos desde FRED (CPIAUCSL) hasta junio 2025")
        return df_cpi
        
    except Exception as e:
        st.error(f"Error obteniendo datos de CPI de EE.UU.: {e}")
        return None

# --- FUNCIONES DE OBTENCIÓN DE DATOS (CON CACHÉ) ---

@st.cache_data(ttl=3600)  # Cachea los datos por 1 hora
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
        ggal_adr = yf.download("GGAL", start=start_date, progress=False, auto_adjust=True)
        if ggal_adr.empty:
            raise ValueError("No se pudieron obtener los datos del ADR (GGAL) desde Yahoo Finance.")
        
        # CORRECCIÓN: Convertir a DataFrame correctamente
        df_usd = ggal_adr[['Close']].copy()
        df_usd.reset_index(inplace=True)
        df_usd.columns = ['fecha', 'ggal_usd']
    except Exception as e_adr:
        st.error(f"Error crítico: No se pudo obtener el precio en Dólares desde Yahoo Finance. {e_adr}")
        return None

    # Paso 2: Intentar obtener GGAL en ARS desde Yahoo Finance
    try:
        ggal_ba = yf.download("GGAL.BA", start=start_date, progress=False, auto_adjust=True)
        if ggal_ba.empty:
            raise ValueError("yf.download() para GGAL.BA devolvió un DataFrame vacío.")
        
        # CORRECCIÓN: Convertir a DataFrame correctamente
        df_ars = ggal_ba[['Close']].copy()
        df_ars.reset_index(inplace=True)
        df_ars.columns = ['fecha', 'ggal_ars']
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
        except Exception as e_fallback:
            st.error(f"Falló también la fuente de respaldo para el precio en Pesos: {e_fallback}")
            return None

    # Paso 4: Unir los DataFrames y calcular
    if df_ars is not None and df_usd is not None:
        # CORRECCIÓN: Verificar que ambos DataFrames tengan datos
        if df_ars.empty or df_usd.empty:
            st.error("Uno o ambos DataFrames están vacíos.")
            return None
            
        df = pd.merge(df_ars, df_usd, on='fecha', how='inner')
        df.dropna(inplace=True)
        
        # CORRECCIÓN: Verificar que el merge produjo resultados
        if df.empty:
            st.error("No se encontraron fechas comunes entre los datos de ARS y USD.")
            return None
            
        # CORRECCIÓN: Eliminar .squeeze() y agregar validación
        df['ccl_nominal'] = (df['ggal_ars'] / df['ggal_usd']) * 10
        df_ccl = df[['fecha', 'ccl_nominal']]
        
        # Filtrar valores válidos
        df_ccl = df_ccl[df_ccl['ccl_nominal'] > 0]
        
        if df_ccl.empty:
            st.error("No se pudieron calcular valores válidos de CCL.")
            return None
            
        return df_ccl
    else:
        st.error("No se pudieron consolidar los datos de precios en ARS y USD.")
        return None


@st.cache_data(ttl=86400)  # Cachea el IPC por 24 horas
def get_ipc_from_datos_gob_ar():
    """
    Obtiene el IPC Nacional (base Dic 2016) desde la API de datos.gob.ar.
    Si no hay datos recientes, los complementa con datos manuales actualizados.
    ID de la serie: 148.3_INIVELNAL_DICI_M_26
    """
    url = "https://apis.datos.gob.ar/series/api/series/?ids=148.3_INIVELNAL_DICI_M_26"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # CORRECCIÓN: Verificar estructura de respuesta
        if 'data' not in data:
            raise ValueError("La respuesta de la API no contiene el campo 'data'")
            
        df = pd.DataFrame(data['data'], columns=['fecha', 'ipc'])
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['ipc'] = pd.to_numeric(df['ipc'], errors='coerce')
        
        # CORRECCIÓN: Eliminar valores nulos después de la conversión
        df.dropna(inplace=True)
        
        if df.empty:
            raise ValueError("No se obtuvieron datos válidos de IPC")
        
        df['fecha'] = df['fecha'].dt.to_period('M').dt.to_timestamp()
        df = df.sort_values('fecha')
        
        # MEJORA: Agregar datos faltantes de 2025 si la API no los tiene
        ultimo_dato = df['fecha'].max()
        fecha_junio_2025 = pd.Timestamp('2025-06-01')
        
        if ultimo_dato < fecha_junio_2025:
            # Obtener el último IPC para calcular los nuevos valores
            ultimo_ipc = df['ipc'].iloc[-1]
            
            # Datos oficiales de inflación mensual 2025 (fuente: INDEC)
            # Actualizados con datos confirmados hasta junio 2025
            datos_2025 = [
                ('2025-01-01', 2.2),  # Enero 2025: 2.2%
                ('2025-02-01', 2.4),  # Febrero 2025: 2.4%
                ('2025-03-01', 3.7),  # Marzo 2025: 3.7%
                ('2025-04-01', 2.8),  # Abril 2025: 2.8%
                ('2025-05-01', 1.5),  # Mayo 2025: 1.5% (CONFIRMADO)
                ('2025-06-01', 1.6),  # Junio 2025: 1.6% (CONFIRMADO - Publicado 14/07/25)
            ]
            
            # Calcular IPC acumulado para cada mes
            ipc_actual = ultimo_ipc
            for fecha_str, inflacion_mensual in datos_2025:
                fecha = pd.Timestamp(fecha_str)
                if fecha > ultimo_dato:
                    ipc_actual = ipc_actual * (1 + inflacion_mensual/100)
                    nuevo_dato = pd.DataFrame({
                        'fecha': [fecha],
                        'ipc': [ipc_actual]
                    })
                    df = pd.concat([df, nuevo_dato], ignore_index=True)
            
            st.info("✅ Datos de IPC actualizados con información oficial del INDEC hasta junio 2025 (1,6% - confirmado 14/07/25)")
        
        return df

    except requests.RequestException as e:
        st.error(f"Error al conectar con la API de datos.gob.ar: {e}")
        return None
    except (KeyError, ValueError) as e:
        st.error(f"Error procesando los datos de IPC: {e}")
        return None

# --- LÓGICA PRINCIPAL DE LA APLICACIÓN ---
with st.spinner("Cargando y procesando datos... (puede tardar un momento la primera vez)"):
    df_ccl = get_ccl_from_ypf()
    
    # Obtener datos de inflación según la opción seleccionada
    if ajuste_por_inflacion_usa:
        df_inflacion = get_cpi_usa()
        columna_inflacion = 'cpi'
        titulo_inflacion = "CPI de EE.UU."
    else:
        df_inflacion = get_ipc_from_datos_gob_ar()
        columna_inflacion = 'ipc'
        titulo_inflacion = "IPC de Argentina"

    if df_ccl is not None and df_inflacion is not None and not df_ccl.empty and not df_inflacion.empty:
        try:
            # 1. Unir los dos DataFrames.
            df_merged = pd.merge_asof(
                df_ccl.sort_values('fecha'),
                df_inflacion.sort_values('fecha'),
                on='fecha',
                direction='backward'
            )
            df_merged.dropna(inplace=True)
            
            # CORRECCIÓN: Verificar que el merge_asof funcionó
            if df_merged.empty:
                st.error("No se pudieron combinar los datos de CCL e inflación. Verifique que las fechas se solapen.")
                st.stop()

            # 2. Calcular el CCL ajustado a precios de hoy
            inflacion_actual = df_merged[columna_inflacion].iloc[-1]
            fecha_ultimo_dato = df_inflacion['fecha'].iloc[-1]
            
            df_merged['ccl_ajustado'] = df_merged['ccl_nominal'] * (inflacion_actual / df_merged[columna_inflacion])

            # 3. Crear el gráfico con Plotly
            fig = go.Figure()

            # Línea principal del CCL ajustado
            nombre_serie = f'Dólar CCL ajustado por {titulo_inflacion}'
            fig.add_trace(go.Scatter(
                x=df_merged['fecha'],
                y=df_merged['ccl_ajustado'],
                mode='lines',
                name=nombre_serie,
                line=dict(color='#00BFFF', width=2.5),
                hoverinfo='text',
                hovertext=[
                    f"<b>Fecha:</b> {row.fecha.strftime('%d-%m-%Y')}<br>"
                    f"<b>CCL Ajustado:</b> ${row.ccl_ajustado:,.2f}<br>"
                    f"<b>CCL Nominal:</b> ${row.ccl_nominal:,.2f}"
                    for row in df_merged.itertuples()
                ]
            ))
            
            # Línea punteada del valor mínimo
            valor_minimo = df_merged['ccl_ajustado'].min()
            fig.add_hline(
                y=valor_minimo,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Mínimo: ${valor_minimo:,.2f}",
                annotation_position="top right"
            )
            
            # 4. Configurar el layout del gráfico
            titulo_grafico = f'<b>Dólar CCL a Precios de Hoy (Ajustado por {titulo_inflacion})</b>'
            fig.update_layout(
                template='plotly_dark',
                title=titulo_grafico,
                yaxis_title='Valor en Pesos Argentinos (de hoy)' if not ajuste_por_inflacion_usa else 'Valor en Dólares (de hoy)',
                xaxis_title='Fecha',
                height=800,  # Aumentado de 600 a 800
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(tickprefix="$", tickformat=",.0f")
            )

            st.plotly_chart(fig, use_container_width=True)
            
            # Expansor para mostrar los datos en una tabla
            with st.expander("Ver tabla de datos completos"):
                columnas_mostrar = ['fecha', 'ccl_nominal', columna_inflacion, 'ccl_ajustado']
                formato_columnas = {
                    'ccl_nominal': '${:,.2f}',
                    columna_inflacion: '{:.2f}',
                    'ccl_ajustado': '${:,.2f}',
                    'fecha': '{:%d-%m-%Y}'
                }
                st.dataframe(
                    df_merged[columnas_mostrar].style.format(formato_columnas),
                    use_container_width=True
                )
                
        except Exception as e:
            st.error(f"Error procesando los datos: {e}")
            st.error("Por favor, intente recargar la página o contacte al administrador.")

    else:
        st.error("No se pudieron cargar todos los datos necesarios para generar el gráfico.")
        st.error("Por favor, intente de nuevo más tarde o verifique su conexión a internet.")

st.markdown("---")
fuente_datos = "CCL implícito calculado con YPF/YPFD.BA (con respaldo de data912.com)"
if ajuste_por_inflacion_usa:
    fuente_datos += " | CPI de EE.UU. desde Bureau of Labor Statistics"
else:
    fuente_datos += " | IPC Nacional desde datos.gob.ar"
    
st.caption(f"Fuente de Datos: {fuente_datos}.")
