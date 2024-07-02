import json
import re
from matplotlib import pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import matplotlib.colors as mcolors

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

s = """{
"knowledge": {"score": 90, "reason": "The user demonstrated an excellent level of knowledge in their field.", "improvement": "To maintain your level, keep reading recent articles in your field."},
"english": {"score": 85, "reason": "The user showed a high level of English proficiency with minimal errors.", "improvement": "Consider engaging in conversations with native speakers to further improve."},
"soft skills": {"score": 40, "reason": "The user’s communication skills are not strong and effective.", "improvement": "Participate in workshops and practice public speaking to improve."},
"visa": {"score": 15, "reason": "The user does not have a high likelihood of obtaining a Canadian visa based on their passport country.", "improvement": "Gather more supporting documents and seek advice from an immigration consultant."}
}"""


s = re.sub(r'[“”]', '"', s)
start = s.find('{')
end = s.rfind('}')
s = s[start:end+1]

scores = json.loads(s)

top_row = st.columns(1)

top_row[0].markdown("Your interview is done. You can view the assessment below.")
top_row[0].markdown("---")

col1, col2 = st.columns((2, 2))
columns = [col1, col2, col1, col2]

for (label, info), col in zip(scores.items(), columns):
    if info['score'] < 5:
        info['score'] = 5

    fig = create_gauge(info['score'], label)
    col.plotly_chart(fig, use_container_width=True)
    col.markdown(f"<div style='min-height: 100px;'>{info['reason']}</div>", unsafe_allow_html=True)

    with col.expander("How to improve?"):
        st.write(info['improvement'])