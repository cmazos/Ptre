import streamlit as st
import pandas as pd
import numpy as np
from backend import mix_waters, makeup_water, calculate_cbe_manual, simulate_scale
from visualizations import plot_stiff, plot_si

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="Scale Predictor App", page_icon="💧", layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    .reportview-container .main .block-container{
        padding-top: 2rem;
    }
    h1 {
        color: #1f77b4;
    }
    h2 {
        color: #ff7f0e;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

st.title("💧 Hydrogeochemical Scale Predictor")
st.markdown("**Simulación Termodinámica de Incrustaciones Minerales usando PHREEQC (Pitzer Database)**")

# --- SIDEBAR: INPUT PARAMETERS ---
st.sidebar.header("⚙️ Configuración del Sistema")

num_waters = st.sidebar.slider("Número de aguas a mezclar", 1, 3, 2)

waters_data = {}
for i in range(1, num_waters + 1):
    st.sidebar.subheader(f"Agua {i} (mg/L)")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.markdown("**Cationes**")
        na = st.number_input(f"Na⁺ (A{i})", 0.0, 300000.0, 10000.0, step=100.0)
        ca = st.number_input(f"Ca²⁺ (A{i})", 0.0, 100000.0, 1000.0, step=10.0)
        mg = st.number_input(f"Mg²⁺ (A{i})", 0.0, 50000.0, 500.0, step=10.0)
        ba = st.number_input(f"Ba²⁺ (A{i})", 0.0, 10000.0, 10.0, step=1.0)
        sr = st.number_input(f"Sr²⁺ (A{i})", 0.0, 10000.0, 50.0, step=1.0)
        fe = st.number_input(f"Fe²⁺/³⁺ (A{i})", 0.0, 10000.0, 5.0, step=1.0)
    with col2:
        st.markdown("**Aniones**")
        cl = st.number_input(f"Cl⁻ (A{i})", 0.0, 300000.0, 16000.0, step=100.0)
        so4 = st.number_input(f"SO₄²⁻ (A{i})", 0.0, 50000.0, 200.0, step=10.0)
        co3 = st.number_input(f"CO₃²⁻ (A{i})", 0.0, 10000.0, 0.0, step=10.0)
        
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            hco3_raw = st.number_input(f"Alcalinidad (A{i})", 0.0, 50000.0, 500.0, step=10.0)
        with col_a2:
            alk_unit = st.selectbox(f"Unidad (A{i})", ["mg HCO3⁻/L", "mg CaCO3/L"])
            
        hco3 = hco3_raw * 1.219 if alk_unit == "mg CaCO3/L" else hco3_raw
        
    st.markdown("**Parámetros Físicos**")
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        ph = st.number_input(f"pH (A{i})", 0.0, 14.0, 7.0, step=0.1)
    with col_p2:
        sg = st.number_input(f"SG (A{i})", 0.5, 2.0, 1.0, step=0.01)
    with col_p3:
        temp_lab = st.number_input(f"Temp Lab °C (A{i})", 0.0, 100.0, 25.0, step=1.0)
    with col_p4:
        tds_input = st.number_input(f"TDS (A{i})", 0.0, 500000.0, 0.0, step=100.0)
        
    waters_data[f'Agua {i}'] = {
        'Na': na, 'Ca': ca, 'Mg': mg, 'Ba': ba, 'Sr': sr, 'Fe': fe,
        'Cl': cl, 'SO4': so4, 'HCO3': hco3, 'CO3': co3,
        'pH': ph, 'SG': sg, 'Temp_Lab': temp_lab, 'TDS': tds_input
    }

st.sidebar.markdown("---")
st.sidebar.subheader("Fracciones de Mezcla (%)")
fractions_raw = {}
if num_waters > 1:
    for i in range(1, num_waters + 1):
        fractions_raw[f'Agua {i}'] = st.sidebar.slider(f"Fracción Agua {i}", 0.0, 100.0, 100.0/num_waters)
    
    # Normalize fractions
    total_frac = sum(fractions_raw.values())
    if total_frac == 0:
        st.sidebar.error("Las fracciones no pueden sumar 0.")
        st.stop()
    fractions = {k: v / total_frac for k, v in fractions_raw.items()}
    st.sidebar.info(f"Fracciones normalizadas suman 100%.")
else:
    fractions = {'Agua 1': 1.0}

st.sidebar.markdown("---")
st.sidebar.subheader("Rangos de Simulación")
t_min, t_max = st.sidebar.slider("Rango de Temperatura (°F)", 50, 400, (77, 212))
t_steps = st.sidebar.number_input("Puntos de Temperatura", 2, 50, 5)

p_min, p_max = st.sidebar.slider("Rango de Presión (psi)", 14, 10000, (14, 1500))
p_steps = st.sidebar.number_input("Puntos de Presión", 1, 10, 2)

t_range = np.linspace(t_min, t_max, t_steps).tolist()
if p_min == p_max:
    p_range = [p_min]
else:
    p_range = np.linspace(p_min, p_max, p_steps).tolist()

st.sidebar.markdown("---")
st.sidebar.subheader("Acciones Secuenciales")
balance_btn = st.sidebar.button("1. Ejecutar Balance Iónico (Reconciliar)", type="primary", use_container_width=True)

if balance_btn:
    mixed_comp = mix_waters(waters_data, fractions)
    adjusted_comp, msg = makeup_water(mixed_comp)
    st.session_state['mixed_comp'] = mixed_comp
    st.session_state['agua_balanceada'] = adjusted_comp
    st.session_state['reporte_balance'] = msg
    st.session_state['df_results'] = None # Reset simulation if new balance is done
    
simulate_btn = st.sidebar.button(
    "2. Correr Simulación Termodinámica", 
    type="secondary", 
    disabled='agua_balanceada' not in st.session_state,
    use_container_width=True
)

# --- MAIN CONTENT ---

tab1, tab2, tab3, tab4 = st.tabs(["📊 Caracterización de Aguas", "🧪 Mezcla y Auto-Ajuste", "📈 Predicción de Incrustaciones (SI)", "💎 Gravedad de Incrustación (Masa)"])

with tab1:
    st.header("Caracterización de Aguas de Entrada")
    cols = st.columns(num_waters)
    for i, (name, comp) in enumerate(waters_data.items()):
        with cols[i]:
            st.subheader(name)
            cbe = calculate_cbe_manual(comp)
            st.metric("Error Balance Cargas (CBE)", f"{cbe:.2f}%", 
                      delta="OK" if abs(cbe) <= 5 else "Requiere Ajuste", delta_color="inverse" if abs(cbe) > 5 else "normal")
            fig = plot_stiff(comp, title=f"Stiff - {name}")
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Cálculo de Mezcla y Balance Iónico")
    if num_waters > 1:
        st.write("Fracciones utilizadas:")
        st.json({k: f"{v*100:.2f}%" for k, v in fractions.items()})
    
    if 'agua_balanceada' in st.session_state:
        msg = st.session_state['reporte_balance']
        if "CBE <" in msg or "No adjustment" in msg:
            st.success(msg)
        else:
            st.warning(msg)
            
        st.subheader("Composición Resultante (Conservativa)")
        df_mixed = pd.DataFrame([st.session_state['mixed_comp']]).T.rename(columns={0: 'Concentración (mg/L)'})
        st.dataframe(df_mixed.style.format("{:.2f}"))
        
        st.subheader("Auto-Ajuste (Make-up)")
        df_adj = pd.DataFrame([st.session_state['agua_balanceada']]).T.rename(columns={0: 'Concentración Ajustada (mg/L)'})
        st.dataframe(df_adj.style.format("{:.2f}"))
        
        fig_mixed = plot_stiff(st.session_state['agua_balanceada'], title="Stiff - Agua Mezclada Ajustada")
        st.plotly_chart(fig_mixed, use_container_width=True)
    else:
        st.info("Presiona '1. Ejecutar Balance Iónico (Reconciliar)' en el panel izquierdo para calcular el Make-up.")

if simulate_btn and 'agua_balanceada' in st.session_state:
    with st.spinner("⏳ Simulando con PHREEQC y base de datos Pitzer. Esto puede tomar unos segundos..."):
        df_results = simulate_scale(st.session_state['agua_balanceada'], t_range, p_range)
        st.session_state['df_results'] = df_results
        st.success("¡Simulación completada con éxito!")

df_results = st.session_state.get('df_results', None)

with tab3:
    st.header("Análisis Termodinámico: Índices de Saturación")
    
    if df_results is not None:
        st.subheader("Tabla de Resultados")
        st.dataframe(df_results.style.format(precision=3))
        
        st.subheader("Gráficos de Tendencia de Incrustación")
        
        col_graph1, col_graph2 = st.columns(2)
        
        with col_graph1:
            fig_caco3 = plot_si(df_results, 'CaCO3')
            st.plotly_chart(fig_caco3, use_container_width=True)
            
            fig_baso4 = plot_si(df_results, 'BaSO4')
            st.plotly_chart(fig_baso4, use_container_width=True)
            
        with col_graph2:
            fig_srso4 = plot_si(df_results, 'SrSO4')
            st.plotly_chart(fig_srso4, use_container_width=True)
            
            fig_caso4 = plot_si(df_results, 'Anhydrite') # Or Gypsum depending on user preference, Anhydrite is common at higher temps
            fig_caso4.update_layout(title="Saturation Index of CaSO4 (Anhydrite) vs Temperature")
            st.plotly_chart(fig_caso4, use_container_width=True)
            
        st.info("""
        **Interpretación Breve:**
        - **SI < 0:** Subsaturado. El mineral tenderá a disolverse. No hay riesgo de incrustación.
        - **SI = 0:** Equilibrio termodinámico.
        - **SI > 0:** Sobresaturado. Riesgo de precipitación (incrustación) del mineral.
        """)
    else:
        st.info("Configura los parámetros en el panel izquierdo y presiona 'Ejecutar Simulación'.")

with tab4:
    st.header("Gravedad de Incrustación (Masa Precipitada)")
    
    if df_results is not None:
        mineral_options = {
            "Carbonato de Calcio (CaCO3)": "Calcita_mg_L",
            "Sulfato de Bario (BaSO4)": "Barita_mg_L",
            "Sulfato de Estroncio (SrSO4)": "Celestita_mg_L",
            "Sulfato de Calcio (Anhidrita)": "Anhidrita_mg_L",
            "Carbonato de Hierro (Siderita)": "Siderita_mg_L"
        }
        
        selected_mineral = st.selectbox("Selecciona el mineral a analizar:", list(mineral_options.keys()))
        col_name = mineral_options[selected_mineral]
        
        tab_lines, tab_heatmap = st.tabs(["📉 Líneas de Tendencia", "🗺️ Mapa de Contorno"])
        
        from visualizations import plot_mass_lines, plot_mass_heatmap
        
        with tab_lines:
            fig_lines = plot_mass_lines(df_results, col_name, title=f"Masa Precipitada de {selected_mineral}")
            st.plotly_chart(fig_lines, use_container_width=True)
            
        with tab_heatmap:
            # Heatmaps require at least 2 unique points for both axes
            if len(df_results['Temperature (F)'].unique()) > 1 and len(df_results['Pressure (psi)'].unique()) > 1:
                fig_heat = plot_mass_heatmap(df_results, col_name, title=f"Mapa Termodinámico: {selected_mineral}")
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.warning("El Mapa de Contorno requiere al menos 2 puntos de Temperatura y 2 puntos de Presión configurados en los rangos de simulación.")
    else:
         st.info("Configura los parámetros en el panel izquierdo y presiona 'Ejecutar Simulación'.")
