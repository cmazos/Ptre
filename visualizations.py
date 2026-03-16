import plotly.graph_objects as go
import pandas as pd
import numpy as np

MOLAR_MASSES = {
    'Na': 22.989769, 'Ca': 40.078, 'Mg': 24.305, 
    'Cl': 35.45, 'SO4': 96.06, 'HCO3': 61.0168,
    'Fe': 55.845, 'CO3': 60.01
}
VALENCES = {
    'Na': 1, 'Ca': 2, 'Mg': 2, 'Cl': -1, 'SO4': -2, 'HCO3': -1
}

def plot_stiff(composition: dict, title: str = "Stiff Diagram"):
    """
    Generates a Stiff diagram using Plotly.
    composition: dict in mg/L
    """
    # Convert mg/L to meq/L
    meq_l = {}
    for cl in ['Na', 'Ca', 'Mg', 'Cl', 'SO4', 'HCO3']:
        conc = composition.get(cl, 0)
        if cl in MOLAR_MASSES:
            meq_l[cl] = (conc / MOLAR_MASSES[cl]) * abs(VALENCES.get(cl, 1))
        else:
            meq_l[cl] = 0
            
    # Stiff diagrams typically map:
    # Left (Cations): Na+K (top), Ca (mid), Mg (bot)
    # Right (Anions): Cl (top), HCO3+CO3 (mid), SO4 (bot)
    
    # In Plotly, we plot a polygon.
    # We will use y values: 3, 2, 1
    # X values: negative for cations, positive for anions
    
    c_na = -meq_l.get('Na', 0)
    c_ca = -meq_l.get('Ca', 0)
    c_mg = -meq_l.get('Mg', 0)
    
    a_cl = meq_l.get('Cl', 0)
    a_hco3 = meq_l.get('HCO3', 0)
    a_so4 = meq_l.get('SO4', 0)
    
    x_coords = [c_na, c_ca, c_mg, 0, a_so4, a_hco3, a_cl, 0]
    y_coords = [3, 2, 1, 0.5, 1, 2, 3, 3.5]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_coords,
        y=y_coords,
        fill='toself',
        fillcolor='rgba(0, 150, 200, 0.5)',
        line=dict(color='blue'),
        mode='lines+markers',
        name='Water Footprint'
    ))
    
    # Add vertical line at 0
    fig.add_vline(x=0, line_width=2, line_color="black")
    
    # Annotations
    annotations = [
        dict(x=-0.5, y=3, text="Na⁺ + K⁺", xanchor='right', showarrow=False),
        dict(x=-0.5, y=2, text="Ca²⁺", xanchor='right', showarrow=False),
        dict(x=-0.5, y=1, text="Mg²⁺", xanchor='right', showarrow=False),
        dict(x=0.5, y=3, text="Cl⁻", xanchor='left', showarrow=False),
        dict(x=0.5, y=2, text="HCO₃⁻ + CO₃²⁻", xanchor='left', showarrow=False),
        dict(x=0.5, y=1, text="SO₄²⁻", xanchor='left', showarrow=False)
    ]
    
    fig.update_layout(
        title=title,
        xaxis_title="meq/L",
        yaxis=dict(showticklabels=False, range=[0, 4]),
        annotations=annotations,
        template='plotly_white',
        height=400
    )
    
    return fig

def plot_si(df: pd.DataFrame, mineral: str):
    """
    Plots Saturation Index vs Temperature, segregated by Pressure.
    """
    fig = go.Figure()
    
    # Get unique pressures
    pressures = df['Pressure (psi)'].unique()
    
    col_name = [col for col in df.columns if mineral in col][0]
    
    for p in pressures:
        df_p = df[df['Pressure (psi)'] == p]
        
        # Determine if SI > 0 (Scaling tendency)
        # We can color parts of the line or just the line itself
        fig.add_trace(go.Scatter(
            x=df_p['Temperature (F)'],
            y=df_p[col_name],
            mode='lines+markers',
            name=f'P = {p} psi',
            hovertemplate='T: %{x} °F<br>SI: %{y:.2f}'
        ))
        
    # Add horizontal line at SI = 0 (equilibrium)
    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Equilibrium (SI=0)")
    
    fig.update_layout(
        title=f'Saturation Index of {mineral} vs Temperature',
        xaxis_title='Temperature (°F)',
        yaxis_title='Saturation Index (SI)',
        template='plotly_white',
        hovermode='x unified',
        legend_title='Pressure'
    )
    
    return fig

import plotly.express as px

def plot_mass_lines(df: pd.DataFrame, col_name: str, title: str):
    """
    Plots precipitated mass (mg/L) vs Temperature, segregated by Pressure.
    """
    fig = px.line(
        df, 
        x='Temperature (F)', 
        y=col_name, 
        color='Pressure (psi)',
        markers=True,
        title=title,
        labels={'Temperature (F)': 'Temperatura (°F)', col_name: 'Masa Incrustante (mg/L)', 'Pressure (psi)': 'Presión (psi)'}
    )
    fig.update_layout(template='plotly_white', hovermode='x unified')
    return fig

def plot_mass_heatmap(df: pd.DataFrame, col_name: str, title: str):
    """
    Plots a thermodynamic contour map of precipitated mass (mg/L) across varying Temperature and Pressure.
    """
    # Create 2D grid
    pivot_df = df.pivot(index='Pressure (psi)', columns='Temperature (F)', values=col_name)
    
    # Use a colorscale from green (low scale) to red (high scale)
    fig = go.Figure(data=go.Contour(
        z=pivot_df.values,
        x=pivot_df.columns, # Temperature
        y=pivot_df.index,   # Pressure
        colorscale=[[0.0, 'green'], [0.5, 'yellow'], [1.0, 'darkred']],
        colorbar=dict(title='Masa (mg/L)')
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Temperatura (°F)',
        yaxis_title='Presión (psi)',
        template='plotly_white'
    )
    return fig
