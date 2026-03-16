import numpy as np
import pandas as pd
from phreeqpython import PhreeqPython

# Instantiate PhreeqPython with the Pitzer database
try:
    pp = PhreeqPython(database='pitzer.dat')
except Exception as e:
    # Fallback or error handling if pitzer.dat is not found in the environment.
    # Usually phreeqpython comes with pitzer.dat.
    print(f"Error loading pitzer.dat: {e}")
    pp = PhreeqPython() # Fallback, but might not be pitzer

# Molar masses (g/mol) for conversions if needed
# Note: phreeqpython expects concentrations in mmol/kgw or mg/L usually, we'll input mg/L.
MOLAR_MASSES = {
    'Na': 22.989769,
    'Ca': 40.078,
    'Mg': 24.305,
    'Ba': 137.327,
    'Sr': 87.62,
    'Fe': 55.845,
    'Cl': 35.45,
    'SO4': 96.06,
    'HCO3': 61.0168,
    'CO3': 60.008
}

VALENCES = {
    'Na': 1,
    'Ca': 2,
    'Mg': 2,
    'Ba': 2,
    'Sr': 2,
    'Fe': 2,
    'Cl': -1,
    'SO4': -2,
    'HCO3': -1,
    'CO3': -2
}

def calculate_cbe_manual(composition: dict) -> float:
    """
    Calculates the Charge Balance Error (CBE) manually based on mg/L inputs.
    composition: dict with keys 'Na', 'Ca', 'Mg', 'Ba', 'Sr', 'Cl', 'SO4', 'HCO3' in mg/L.
    Returns CBE in percentage.
    """
    cations_meq_l = 0.0
    anions_meq_l = 0.0

    for ion, conc in composition.items():
        if ion in MOLAR_MASSES and conc > 0:
            meq_l = (conc / MOLAR_MASSES[ion]) * abs(VALENCES[ion])
            if VALENCES[ion] > 0:
                cations_meq_l += meq_l
            else:
                anions_meq_l += meq_l
                
    if (cations_meq_l + anions_meq_l) == 0:
        return 0.0
        
    cbe = ((cations_meq_l - anions_meq_l) / (cations_meq_l + anions_meq_l)) * 100
    return cbe

def makeup_water(composition: dict) -> tuple[dict, str]:
    """
    Adjusts the water composition using Na+ or Cl- to ensure CBE <= 2%.
    """
    cbe = calculate_cbe_manual(composition)
    adjusted_comp = composition.copy()
    message = f"Initial CBE: {cbe:.2f}%. "

    if abs(cbe) <= 2.0:
        message += "CBE < 2%, no adjustment needed."
        return adjusted_comp, message

    # Calculate current milliequivalents
    cations_meq_l = sum((adjusted_comp.get(ion, 0) / MOLAR_MASSES[ion]) * abs(VALENCES[ion]) 
                        for ion in ['Na', 'Ca', 'Mg', 'Ba', 'Sr', 'Fe'] if adjusted_comp.get(ion, 0) > 0)
    anions_meq_l = sum((adjusted_comp.get(ion, 0) / MOLAR_MASSES[ion]) * abs(VALENCES[ion]) 
                       for ion in ['Cl', 'SO4', 'HCO3', 'CO3'] if adjusted_comp.get(ion, 0) > 0)

    if cations_meq_l > anions_meq_l:
        # Need more anions -> Add Cl-
        diff_meq = cations_meq_l - anions_meq_l
        added_cl_mg = diff_meq * MOLAR_MASSES['Cl']
        adjusted_comp['Cl'] = adjusted_comp.get('Cl', 0) + added_cl_mg
        message += f"Adjusted by adding {added_cl_mg:.2f} mg/L of Cl-."
    else:
        # Need more cations -> Add Na+
        diff_meq = anions_meq_l - cations_meq_l
        added_na_mg = diff_meq * MOLAR_MASSES['Na']
        adjusted_comp['Na'] = adjusted_comp.get('Na', 0) + added_na_mg
        message += f"Adjusted by adding {added_na_mg:.2f} mg/L of Na+."

    return adjusted_comp, message

def mix_waters(waters_dict: dict, fractions: dict) -> dict:
    """
    Mixes multiple waters based on volumetric fractions.
    waters_dict: {'Water 1': comp_dict_1, 'Water 2': comp_dict_2, ...}
    fractions: {'Water 1': 0.5, 'Water 2': 0.5}
    """
    mixed_comp = {}
    
    # Identify all unique keys (ions + physical parameters)
    all_keys = set()
    for w_data in waters_dict.values():
        all_keys.update(w_data.keys())
        
    for key in all_keys:
        mixed_conc = 0.0
        for w_name, comp in waters_dict.items():
            mixed_conc += comp.get(key, 0) * fractions.get(w_name, 0)
        mixed_comp[key] = mixed_conc
        
    return mixed_comp

def simulate_scale(composition: dict, t_range: list, p_range: list) -> pd.DataFrame:
    """
    Simulates scaling tendencies using phreeqpython and raw PHREEQC input strings for thermodynamic rigor.
    t_range: list of temperatures in Fahrenheit.
    p_range: list of pressures in psi.
    Returns a DataFrame with SI values and precipitated mass.
    """
    pp = PhreeqPython(database='pitzer.dat')
    results = []
    
    ph = composition.get('pH', 7.0)
    density = composition.get('SG', 1.0)
    temp_lab = composition.get('Temp_Lab', 25.0)
    
    # Calculate TDS by summing all ionic concentrations if not provided
    tds_input = composition.get('TDS', 0)
    if tds_input > 0:
        tds = tds_input
    else:
        tds = sum(val for key, val in composition.items() if key in MOLAR_MASSES)
    
    # Calculate exact water mass in kg
    masa_agua_kg = max(0.0001, density - (tds / 1_000_000.0))
    
    alkalinity_total = composition.get('HCO3', 0) + composition.get('CO3', 0)
    
    # Base PHREEQC Script using native string format
    base_script = f"""
SOLUTION 1 Agua de Entrada
temp {temp_lab}
pH {ph}
density {density}
water {masa_agua_kg}
units mg/L
Na {composition.get('Na', 0)}
Ca {composition.get('Ca', 0)}
Mg {composition.get('Mg', 0)}
Ba {composition.get('Ba', 0)}
Sr {composition.get('Sr', 0)}
Fe {composition.get('Fe', 0)}
Cl {composition.get('Cl', 0)}
S(6) {composition.get('SO4', 0)}
Alkalinity {alkalinity_total} as HCO3
"""

    for T_F in t_range:
        T_C = (T_F - 32) * 5.0 / 9.0
        
        for P_psi in p_range:
            P_atm = P_psi / 14.6959
            
            script = base_script + f"""
REACTION_TEMPERATURE 1
{T_C}

REACTION_PRESSURE 1
{P_atm}

EQUILIBRIUM_PHASES 1
Calcite 0.0 0.0
Barite 0.0 0.0
Celestite 0.0 0.0
Anhydrite 0.0 0.0
Gypsum 0.0 0.0
Siderite 0.0 0.0

SELECTED_OUTPUT 1
-reset false
-step true
-pH true
-temperature true
-si Calcite Barite Celestite Anhydrite Gypsum Siderite
-equilibrium_phases Calcite Barite Celestite Anhydrite Gypsum Siderite
"""
            try:
                pp.ip.run_string(script)
                out = pp.ip.get_selected_output_array()
                
                # out[0] is headers, out[1] is step -99 (initial), out[2] is step 1 (reacted)
                if len(out) >= 3:
                    headers = out[0]
                    res_row = out[2]
                    
                    data = dict(zip(headers, res_row))
                    
                    # Moles precipitated * Molecular Weight * 1000 = mg/L
                    # d_Mineral returns positive moles when mineral precipitates from 0 initial state
                    m_calc = max(0.0, data.get('d_Calcite', 0.0)) * 100.09 * 1000
                    m_bar = max(0.0, data.get('d_Barite', 0.0)) * 233.39 * 1000
                    m_cel = max(0.0, data.get('d_Celestite', 0.0)) * 183.68 * 1000
                    m_anh = max(0.0, data.get('d_Anhydrite', 0.0)) * 136.14 * 1000
                    m_sid = max(0.0, data.get('d_Siderite', 0.0)) * 115.86 * 1000
                    
                    results.append({
                        'Temperature (F)': T_F,
                        'Pressure (psi)': P_psi,
                        'SI_CaCO3 (Calcite)': data.get('si_Calcite', np.nan),
                        'Calcita_mg_L': m_calc,
                        'SI_BaSO4 (Barite)': data.get('si_Barite', np.nan),
                        'Barita_mg_L': m_bar,
                        'SI_SrSO4 (Celestite)': data.get('si_Celestite', np.nan),
                        'Celestita_mg_L': m_cel,
                        'SI_CaSO4 (Anhydrite)': data.get('si_Anhydrite', np.nan),
                        'Anhidrita_mg_L': m_anh,
                        'SI_CaSO4:2H2O (Gypsum)': data.get('si_Gypsum', np.nan),
                        'SI_FeCO3 (Siderite)': data.get('si_Siderite', np.nan),
                        'Siderita_mg_L': m_sid
                    })
                else:
                    raise Exception("Unexpected output array size from PHREEQC")
                    
            except Exception as e:
                print(f"Error simulating at T={T_F}F, P={P_psi}psi: {e}")
                results.append({
                    'Temperature (F)': T_F,
                    'Pressure (psi)': P_psi,
                    'SI_CaCO3 (Calcite)': np.nan,
                    'Calcita_mg_L': np.nan,
                    'SI_BaSO4 (Barite)': np.nan,
                    'Barita_mg_L': np.nan,
                    'SI_SrSO4 (Celestite)': np.nan,
                    'Celestita_mg_L': np.nan,
                    'SI_CaSO4 (Anhydrite)': np.nan,
                    'Anhidrita_mg_L': np.nan,
                    'SI_CaSO4:2H2O (Gypsum)': np.nan,
                    'SI_FeCO3 (Siderite)': np.nan,
                    'Siderita_mg_L': np.nan
                })
                
    return pd.DataFrame(results)
