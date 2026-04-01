import streamlit as st
import streamlit.components.v1 as components
import base64
import json
import time
import re

from ric_backend import extract_ric_graph, generate_mermaid

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
st.markdown("Upload images of an archival record (multi-page supported) to extract standard Entities and Relationships and visualize the archival graph.")

# ==========================
# FILE UPLOAD
# ==========================
uploaded_files = st.file_uploader(
    "Upload Archival Record Image(s)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

# ==========================
# PROCESS BUTTON
# ==========================
if st.button("Extract RiC Graph") and uploaded_files:
    with st.spinner("Analyzing with AI..."):
        image_base64_list = []
        image_bytes_list = []

        for file in uploaded_files:
            bytes_data = file.getvalue()
            image_bytes_list.append(bytes_data)

            b64 = base64.b64encode(bytes_data).decode("utf-8")
            image_base64_list.append(b64)

        results = extract_ric_graph(image_base64_list)

        st.session_state.results = results
        st.session_state.images = image_bytes_list

        if results and results.get("entities"):
            st.session_state.mermaid_code = generate_mermaid(results)
        else:
            st.session_state.mermaid_code = None

# ==========================
# DISPLAY RESULTS
# ==========================
if st.session_state.results:

    # --------------------------
    # DISPLAY IMAGES
    # --------------------------
    st.subheader("Source Documents")

    if st.session_state.images:
        cols = st.columns(len(st.session_state.images))
        for i, img in enumerate(st.session_state.images):
            cols[i].image(img, caption=f"Image {i+1}", width="stretch")

    results = st.session_state.results

    # --------------------------
    # JSON
    # --------------------------
    st.markdown("### 📋 Structured JSON (RiC-CM 1.0)")
    st.json(results)

    st.download_button(
        label="Download JSON",
        data=json.dumps(results, indent=2),
        file_name="ric_analysis.json",
        mime="application/json"
    )

    # --------------------------
    # GRAPH
    # --------------------------
    if results.get("entities"):
        st.markdown("### 🕸️ Visual Archival Graph")

        mermaid_code = st.session_state.mermaid_code

        import mermaid as md

        svg_html = None

        # Retry logic (fix API 503)
        for attempt in range(3):
            try:
                graph = md.Mermaid(mermaid_code)
                svg_html = graph._repr_html_()
                break
            except Exception:
                time.sleep(2)

        # --------------------------
        # FALLBACK
        # --------------------------
        if svg_html is None:
            st.error("⚠️ Mermaid rendering failed (API unavailable).")
            st.code(mermaid_code, language="mermaid")

        else:
            st.session_state.svg_html = svg_html

            # --------------------------
            # CLEAN SVG
            # --------------------------
            clean_svg = None
            match = re.search(r"<svg.*?</svg>", svg_html, re.DOTALL)
            if match:
                clean_svg = match.group(0)

            st.download_button(
                "Download Graph (SVG)",
                data=clean_svg if clean_svg else mermaid_code,
                file_name="ric_graph.svg",
                mime="image/svg+xml"
            )

            # --------------------------
            # ZOOM GRAPH
            # --------------------------
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

            components.html(zoom_html, height=900, scrolling=False)

        # --------------------------
        # MERMAID CODE
        # --------------------------
        with st.expander("View Mermaid Syntax"):
            st.code(mermaid_code, language="mermaid")
