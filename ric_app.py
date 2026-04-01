import streamlit as st
import streamlit.components.v1 as components
import base64
import json
import pandas as pd
import time
import re

from ric_backend import extract_ric_graph, generate_mermaid, extract_ric_graph_from_data

# ==========================
# SESSION STATE INIT
# ==========================
if "results" not in st.session_state:
    st.session_state.results = None

if "images" not in st.session_state:
    st.session_state.images = None

if "mermaid_code" not in st.session_state:
    st.session_state.mermaid_code = None

if "svg_html" not in st.session_state:
    st.session_state.svg_html = None

# ==========================
# PAGE CONFIG
# ==========================
st.set_page_config(page_title="RiC-Mapper: Archival Description", layout="wide")

st.title("🏛️ RiC-Mapper: Automated Archival Description (RiC-CM 1.0)")
st.markdown("Upload images or metadata spreadsheets (Excel/CSV) of archival records to extract standard Entities and Relationships and visualize the archival graph.")

def render_results(results):
    if not results or not results.get("entities"):
        st.error("Failed to extract meaningful entities. Please try again or check your API key.")
        return
        
    st.markdown("### 📋 Structured JSON (RiC-CM 1.0)")
    st.json(results)
        
    st.download_button(
        label="Download JSON",
        data=json.dumps(results, indent=2),
        file_name="ric_analysis.json",
        mime="application/json"
    )
        
    st.markdown("### 🕸️ Visual Archival Graph")
    mermaid_code = generate_mermaid(results)
        
    # mermaid-py generates raw SVG via _repr_html_(). 
    # We wrap it in a pan/zoom script so you get native-feeling interactive controls
    import mermaid as md
    graph = md.Mermaid(mermaid_code)
    svg_html = graph._repr_html_()
    zoom_html = f"""
        <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
        <div id="graph-container" style="width: 100%; height: 95vh;">
            {svg_html}
        </div>
        <script>
            window.onload = function() {{
                var svgElement = document.querySelector('#graph-container svg');
                if (svgElement) {{
                    svgElement.style.width = '100%';
                    svgElement.style.height = '100%';
                    svgPanZoom(svgElement, {{
                        zoomEnabled: true,
                        controlIconsEnabled: true,
                        fit: true,
                        center: true,
                        minZoom: 0.1
                    }});
                }}
            }};
        </script>
    """
    components.html(zoom_html, height=800, scrolling=False)
        
    with st.expander("View Mermaid Syntax"):
        st.code(mermaid_code, language="mermaid")

# ==========================
# FILE UPLOAD
# ==========================
uploaded_files = st.file_uploader("Upload Archival Record Source(s)", type=["png", "jpg", "jpeg", "xlsx", "csv"], accept_multiple_files=True)

# ==========================
# PROCESS LOGIC
# ==========================
if uploaded_files:
    is_spreadsheet = any(f.name.endswith('.xlsx') or f.name.endswith('.csv') for f in uploaded_files)
    
    if is_spreadsheet:
        file = next(f for f in uploaded_files if f.name.endswith(('.xlsx', '.csv')))
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)
            
        # Fix pyarrow serialization for datetime objects from Excel
        df = df.astype(str)
            
        st.subheader("Tabular Data View")
        st.info("Select one or more rows from the table below to generate their RiC Graph.")
        
        # Streamlit 1.35+ functionality for robust dataframe selection
        event = st.dataframe(df, on_select="rerun", selection_mode="multi-row")
        selected_rows = event.selection.rows
        
        if selected_rows:
            if st.button("Extract RiC Graph"):
                with st.spinner("Analyzing spreadsheet data with AI..."):
                    # Convert only the selected rows to dictionaries
                    selected_data = df.iloc[selected_rows].to_dict(orient="records")
                    data_json = json.dumps(selected_data, default=str, ensure_ascii=False)
                    
                    st.subheader("Extraction Results")
                    results = extract_ric_graph_from_data(data_json)
                    render_results(results)
                    
    else:
        # Existing Image Logic
        if st.button("Extract RiC Graph"):
            with st.spinner("Analyzing with AI..."):
                image_base64_list = []
                
                # Display uploaded images
                st.subheader("Source Documents")
                cols = st.columns(len(uploaded_files))
                for i, file in enumerate(uploaded_files):
                    bytes_data = file.getvalue()
                    b64 = base64.b64encode(bytes_data).decode("utf-8")
                    image_base64_list.append(b64)
                    cols[i].image(bytes_data, caption=file.name, width='stretch')
                    
                # Perform Extraction
                st.subheader("Extraction Results")
                results = extract_ric_graph(image_base64_list)
                render_results(results)