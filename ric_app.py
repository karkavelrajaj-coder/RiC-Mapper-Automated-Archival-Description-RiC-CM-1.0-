import streamlit as st
import streamlit.components.v1 as components
import base64
import json
from ric_backend import extract_ric_graph, generate_mermaid

st.set_page_config(page_title="RiC-Mapper: Archival Description", layout="wide")

st.title("🏛️ RiC-Mapper: Automated Archival Description (RiC-CM 1.0)")
st.markdown("Upload images of an archival record (multi-page supported) to extract standard Entities and Relationships and visualize the archival graph.")

uploaded_files = st.file_uploader("Upload Archival Record Image(s)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
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
                cols[i].image(bytes_data, caption=file.name, use_container_width=True)
                
            # Perform Extraction
            st.subheader("Extraction Results")
            results = extract_ric_graph(image_base64_list)
            
            if not results or not results.get("entities"):
                st.error("Failed to extract meaningful entities. Please try again or check your API key.")
            else:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("### 📋 Structured JSON (RiC-CM 1.0)")
                    st.json(results)
                    
                    st.download_button(
                        label="Download JSON",
                        data=json.dumps(results, indent=2),
                        file_name="ric_analysis.json",
                        mime="application/json"
                    )
                    
                with col2:
                    st.markdown("### 🕸️ Visual Archival Graph")
                    mermaid_code = generate_mermaid(results)
                    
                    # Rendering via the mermaid-py Python package
                    import mermaid as md
                    graph = md.Mermaid(mermaid_code)
                    
                    # mermaid-py generates raw SVG via _repr_html_(). 
                    # We wrap it in a pan/zoom script so you get native-feeling interactive controls
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
                    import streamlit.components.v1 as components
                    components.html(zoom_html, height=800, scrolling=False)
                    
                    with st.expander("View Mermaid Syntax"):
                        st.code(mermaid_code, language="mermaid")
