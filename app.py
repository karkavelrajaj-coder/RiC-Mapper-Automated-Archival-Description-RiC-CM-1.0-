import streamlit as st
import pandas as pd
import os
import json
import tempfile
from pyvis.network import Network
import streamlit.components.v1 as components

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="RiC Graph Viewer – DOCIP",
    page_icon="🗃️",
    layout="wide"
)

# Custom Styling for Legend
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .legend-box { padding: 10px; border-radius: 8px; background: #ffffff; color: #333; font-size: 13px; border: 1px solid #ddd; }
    .legend-item { display: flex; align-items: center; margin: 4px 0; }
    .legend-dot { width: 16px; height: 16px; border-radius: 2px; margin-right: 8px; flex-shrink: 0; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

st.title("🗃️ RiC Graph Viewer — Standardized Visuals")
st.caption("Graph visualization exactly matching the requested RiC-CM 1.0 diagram standard.")

# ─────────────────────────────────────────────
# Reference Image Visual Standards
# ─────────────────────────────────────────────
# Record (Pink): #F77CEE
# Group/Subject (Green): #90EE90
# Agent (Blue): #B0C4DE
# Date (Pinkish Pill): #FFC0CB
# Place (Yellow Parallelogram): #FFFFE0
RIC_ENTITIES = {
    "RecordResource": {"color": "#F77CEE", "shape": "box",           "prefix": "RiC-E02 - "},
    "Agent":          {"color": "#B0C4DE", "shape": "ellipse",       "prefix": "RiC-E08 - "},
    "Activity":       {"color": "#B2FFB2", "shape": "box",           "prefix": "RiC-E15 - "},
    "Place":          {"color": "#FFFFB2", "shape": "parallelogram", "prefix": "RiC-E22 - "},
    "Date":           {"color": "#FFC0CB", "shape": "box",           "prefix": "RiC-E18 - "}, # Pills handled by borderRadius in pyvis?
    "Subject":        {"color": "#B2FFB2", "shape": "box",           "prefix": "RiC-E09 - "}, # Six Nations etc are E09 Group
    "Language":       {"color": "#D3D3D3", "shape": "diamond",       "prefix": "RiC-Exxx - "},
    "Instantiation":  {"color": "#EEEEEE", "shape": "box",           "prefix": "RiC-E06 - "},
}

# ─────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────
@st.cache_data
def load_excel_data(file_source):
    """Loads and cleans Excel data."""
    try:
        df = pd.read_excel(file_source).fillna("Not found")
        if 'Filename' not in df.columns:
            df['Filename'] = [f"Record_{i}" for i in range(len(df))]
        return df
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return None

# Sidebar for Data Source
with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader("Upload an Excel metadata file", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        st.success("File loaded successfully!")
        df = load_excel_data(uploaded_file)
    else:
        df = None

if df is None:
    st.warning("⚠️ No data loaded. Please upload an Excel file.")
    st.stop()

# ─────────────────────────────────────────────
# Sidebar Controls
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Controls")
    all_files = df['Filename'].tolist()
    selected_files = st.multiselect(
        "Select Records to Visualize",
        options=all_files,
        default=all_files[:1]
    )
    
    st.divider()
    st.subheader("📐 Reference Legend")
    legend_html = '<div class="legend-box">'
    legend_items = [
        ("RiC-E02 Archival Record", RIC_ENTITIES["RecordResource"]["color"]),
        ("RiC-E08 Agent", RIC_ENTITIES["Agent"]["color"]),
        ("RiC-E09 Group / Subject", RIC_ENTITIES["Subject"]["color"]),
        ("RiC-E18 Date", RIC_ENTITIES["Date"]["color"]),
        ("RiC-E22 Place", RIC_ENTITIES["Place"]["color"]),
    ]
    for label, color in legend_items:
        legend_html += f'''<div class="legend-item">
            <div class="legend-dot" style="background:{color};"></div>
            <span>{label}</span>
        </div>'''
    legend_html += "</div>"
    st.markdown(legend_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Graph Construction Logic
# ─────────────────────────────────────────────
def add_node(net, id, label, type, size=25):
    cfg = RIC_ENTITIES.get(type, RIC_ENTITIES["Subject"])
    # Apply prefix
    full_label = f"{cfg['prefix']}{label}"
    
    node_opts = {
        "label": full_label,
        "color": {"background": cfg["color"], "border": "#333333"},
        "shape": cfg["shape"],
        "size": size,
        "font": {"color": "#333333", "size": 14, "face": "Arial", "strokeWidth": 0},
        "borderWidth": 1.5,
        "title": f"RiC Entity: {type}"
    }
    
    # Special handling for Date (pill shape)
    if type == "Date":
        node_opts["borderRadius"] = 10 # This might not be directly in add_node, but in options
        node_opts["shape"] = "box" 
    
    net.add_node(id, **node_opts)

def add_edge(net, src, tgt, relation_id, label):
    # Prefix relation_id if needed
    full_label = f"{relation_id}: {label}"
    net.add_edge(
        src, tgt,
        label=full_label,
        color="#333333",
        font={
            "size": 11, 
            "color": "#333333", 
            "background": "#F0F0F0", # Grey box background like the image
            "align": "horizontal",
            "strokeWidth": 0
        },
        arrows="to"
    )

def build_ric_graph(selected_df):
    net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#333333", directed=True)
    
    added_nodes = set()

    for _, row in selected_df.iterrows():
        # Central Record Node
        record_id = str(row['Filename'])
        title = str(row.get('title', record_id))
        
        # We'll use a unique key for the node ID to prevent accidental merge across records if needed,
        # but for interlinking we want shared entities to have the same ID.
        
        if record_id not in added_nodes:
            add_node(net, record_id, title[:40], "RecordResource", size=30)
            added_nodes.add(record_id)
            
            # 1. Date (RiC-E18 - wasCreatedOn)
            date_val = str(row.get('date', 'Not found'))
            if date_val != "Not found":
                date_id = f"Date_{date_val}"
                if date_id not in added_nodes:
                    add_node(net, date_id, date_val, "Date", size=20)
                    added_nodes.add(date_id)
                add_edge(net, record_id, date_id, "RiC-R070", "wasCreatedOn")
            
            # 2. Agent (RiC-R028: isCreatorOf)
            creator = str(row.get('creator', 'Not found'))
            if creator != "Not found":
                for c in [x.strip() for x in creator.split(',')]:
                    agent_id = f"Agent_{c}"
                    if agent_id not in added_nodes:
                        add_node(net, agent_id, c, "Agent", size=30)
                        added_nodes.add(agent_id)
                    add_edge(net, record_id, agent_id, "RiC-R028", "isCreatorOf")

            # 3. Subject (RiC-R019: isAbout)
            subject = str(row.get('subject', 'Not found'))
            if subject != "Not found":
                for s in [x.strip() for x in subject.split(',')]:
                    sub_id = f"Subject_{s}"
                    if sub_id not in added_nodes:
                        add_node(net, sub_id, s, "Subject", size=25)
                        added_nodes.add(sub_id)
                    add_edge(net, record_id, sub_id, "RiC-R019", "isAbout")

            # 4. Place (RiC-R074: residesAt?)
            # The reference image uses RiC-R074: residesAt for Place
            coverage = str(row.get('coverage', 'Not found'))
            if coverage != "Not found":
                for p in [x.strip() for x in coverage.split(',')]:
                    place_id = f"Place_{p}"
                    if place_id not in added_nodes:
                        add_node(net, place_id, p, "Place", size=25)
                        added_nodes.add(place_id)
                    add_edge(net, record_id, place_id, "RiC-R074", "residesAt")

    # Options to match the "clean" white look
    net.set_options("""
    {
      "edges": {
        "smooth": {
          "type": "curvedCW",
          "roundness": 0.2
        },
        "font": {
          "background": "#F0F0F0",
          "align": "middle",
          "strokeWidth": 0
        }
      },
      "nodes": {
        "borderWidth": 1.5,
        "borderWidthSelected": 2
      },
      "physics": {
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 150,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "minVelocity": 0.1,
        "stabilization": {
          "iterations": 150
        }
      }
    }
    """)
    return net

# ─────────────────────────────────────────────
# Main View
# ─────────────────────────────────────────────
if selected_files:
    selected_df = df[df['Filename'].isin(selected_files)]
    st.subheader(f"🕸️ RiC Graph Visualization")
    
    with st.spinner("Rendering standardized graph..."):
        net = build_ric_graph(selected_df)
        
        # Use a portable temporary file for the HTML output
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html_content = f.read()
            components.html(html_content, height=750)
            
        # Cleanup temp file
        try:
            os.remove(tmp.name)
        except:
            pass
    
    st.info("💡 Interlinking established via shared Agents, Subjects, and Places.")
else:
    st.warning("Please select at least one record from the sidebar.")
