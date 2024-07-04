import streamlit as st

# Initialize the session state variable
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'Tab 1'

# Define a function to switch tabs
def switch_tab(tab_name):
    st.session_state.active_tab = tab_name

# Create buttons to switch tabs
st.sidebar.button("Go to Tab 1", on_click=switch_tab, args=('Tab 1',))
st.sidebar.button("Go to Tab 2", on_click=switch_tab, args=('Tab 2',))
st.sidebar.button("Go to Tab 3", on_click=switch_tab, args=('Tab 3',))

# Create tabs
tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])

# Content for Tab 1
if st.session_state.active_tab == 'Tab 1':
    with tab1:
        st.header("This is Tab 1")
        st.write("Content for Tab 1")

# Content for Tab 2
if st.session_state.active_tab == 'Tab 2':
    with tab2:
        st.header("This is Tab 2")
        st.write("Content for Tab 2")

# Content for Tab 3
if st.session_state.active_tab == 'Tab 3':
    with tab3:
        st.header("This is Tab 3")
        st.write("Content for Tab 3")