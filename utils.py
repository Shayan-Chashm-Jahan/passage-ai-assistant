import streamlit as st
import re
from streamlit_option_menu import option_menu
import plotly.graph_objects as go


### --- Visuals --- ###

def cleaned_response(response):
    # cleaned_response = re.sub(r'【\d+:\d+†source】', '', response)
    # return cleaned_response
    return response

def get_color(score):
    if score > 75:
        return "#006400"  # DarkGreen
    if score > 50:
        return "#228B22"  # ForestGreen
    if score > 25:
        return "#FFD700"  # Gold
    return "#B22222"  # Firebrick

def create_gauge(score, label):
    color = get_color(score)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={'text': label.capitalize()},
        number={'font': {'color': "white"}}, 
        gauge={
            'axis': {'range': [0, 100], 'tickvals': []},
            'bar': {'color': color},
            'bordercolor': "white",
            'borderwidth': 0,
            'bgcolor': "white",
            'steps': [
                {'range': [0, 100], 'color': 'white'}
            ],
            'threshold': {
                'line': {'color': color, 'width': 4},
                'thickness': 0.7,
                'value': score
            },
            'shape': 'angular'
        }
    ))

    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        height=90,
    )

    return fig