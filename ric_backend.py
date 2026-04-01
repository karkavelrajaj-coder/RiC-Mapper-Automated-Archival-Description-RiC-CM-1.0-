import os
import base64
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RIC_SYSTEM_PROMPT = """You are an expert archivist specialized in the Records in Contexts (RiC-CM 1.0) standard.
Your task is to analyze the provided archival document image(s) (which may represent multiple pages of a single "Record Resource") and extract the core entities and their relationships according to the RiC conceptual model.

The core entities you should identify if present:
- RiC-E02: Record Resource (the document itself)
- RiC-E08: Person
- RiC-E09: Group (e.g., organizations, authorities)
- RiC-E22: Place
- RiC-E18: Date
- RiC-E15: Activity (e.g., Registration, Issuance)

Key Relationships (RiC-R) to identify between these entities:
- RiC-R019: isAbout / RiC-R020: isSubjectOf
- RiC-R028: isCreatorOf / RiC-R027: wasCreatedBy
- RiC-R087: wasBornAt
- RiC-R067: isChildOf
- RiC-R074: residesAt
- RiC-R070: hasBirthDate
- RiC-R070: wasCreatedOn
- RiC-R034: resultedFrom
- RiC-R132: hasOriginIn / RiC-R133: isOriginOf

Respond ONLY with a valid JSON document matching this exact schema:
{
  "entities": [
    {
      "id": "A unique identifier for the graph (string, e.g., 'Record1', 'Person1', 'Group1', 'Place1', 'Date1', 'Activity1')",
      "type": "The RiC Type code (e.g., 'RiC-E02')",
      "label": "The literal extracted value (e.g., 'Elisabeth Verena Bar' or the specific date string '30-10-1918'). NEVER use an abstract category here like 'Entry Date'.",
      "description": "The contextual meaning or category of the entity (e.g., 'Entry Date of the prisoner', 'Mother of Elisabeth')"
    }
  ],
  "relations": [
    {
      "source": "The ID of the source entity",
      "target": "The ID of the target entity",
      "type": "The RiC Relation code (e.g., 'RiC-R019')",
      "label": "A short, readable label for the relation (e.g., 'isAbout')"
    }
  ]
}
Make sure all IDs used in relationships exist in the entities array. Treat all provided images as part of the same parent Record Resource unless there's clear evidence otherwise.
"""

def extract_ric_graph(image_base64_list):
    messages = [
        {"role": "system", "content": RIC_SYSTEM_PROMPT},
        {"role": "user", "content": []}
    ]
    
    text_content = {"type": "text", "text": "Please analyze these pages of an archival record and extract the RiC graph as JSON."}
    messages[1]["content"].append(text_content)
    
    for base64_image in image_base64_list:
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for optimal vision/json abilities
            temperature=0.0,
            messages=messages,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error making API request or parsing JSON: {e}")
        return {"entities": [], "relations": []}

def extract_ric_graph_from_data(json_data):
    messages = [
        {"role": "system", "content": RIC_SYSTEM_PROMPT},
        {"role": "user", "content": f"Please map the following structured archival data into the RiC graph JSON format.\n\nCRITICAL INSTRUCTION: Be extremely exhaustive! Extract EVERY possible Entity (Persons, Groups, Dates, Places, Activities like Data Entry or Record Creation) and forge as many logical RiC-R relationships as possible. Do not leave any meaningful column data out. If a maiden name or previous identity exists, represent it appropriately in the relationships. Treat each row as a central Record Resource.\n\nHere is the JSON data:\n\n{json_data}"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for complex text reasoning too
            temperature=0.0,
            messages=messages,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error making API request or parsing JSON: {e}")
        return {"entities": [], "relations": []}

def generate_mermaid(graph_data):
    lines = ["graph TD"]
    
    entities = graph_data.get("entities", [])
    relations = graph_data.get("relations", [])
    
    # Defaults and mappings
    style_map = {
        "RiC-E02": "#f9f", # Record Resource
        "RiC-E08": "#bbf", # Person
        "RiC-E09": "#bfb", # Group
        "RiC-E22": "#ffb", # Place
        "RiC-E18": "#fbf", # Date
        "RiC-E15": "#bff", # Activity
    }
    
    # Map entity types to Mermaid shape open/close brackets
    shape_map = {
        "RiC-E02": ("[", "]"),    # Record Resource: Rectangle
        "RiC-E08": ("(", ")"),    # Person: Rounded Rectangle
        "RiC-E09": ("(", ")"),    # Group: Rounded Rectangle
        "RiC-E22": ("[/", "/]"),  # Place: Parallelogram
        "RiC-E18": ("([", "])"),  # Date: Stadium
        "RiC-E15": ("{{", "}}"),  # Activity: Hexagon
    }
    
    node_types = {}
    
    # Entities
    lines.append("    %% Entities")
    for entity in entities:
        e_id = entity.get("id")
        e_type = entity.get("type", "Unknown")
        e_label = entity.get("label", "").replace('"', "'")
        node_types[e_id] = e_type
        
        # Get shape brackets (default to rectangle if unknown)
        s_open, s_close = shape_map.get(e_type, ("[", "]"))
        
        # Format: ID["Type - Label"] -> ID(Type - Label) depending on shape
        node_str = f'    {e_id}{s_open}"{e_type} - {e_label}"{s_close}'
        lines.append(node_str)
        
    lines.append("")
    
    # Relations
    lines.append("    %% Relationships")
    for rel in relations:
        source = rel.get("source")
        target = rel.get("target")
        r_type = rel.get("type", "")
        r_label = rel.get("label", "relatedTo")
        
        # Format: source -- "Type: Label" --> target
        edge_str = f'    {source} -- "{r_type}: {r_label}" --> {target}'
        lines.append(edge_str)
        
    lines.append("")
    
    # Styling
    lines.append("    %% Styling")
    for e_id, e_type in node_types.items():
        color = style_map.get(e_type, "#eee")
        lines.append(f"    style {e_id} fill:{color},stroke:#333,stroke-width:2px")
        
    return "\n".join(lines)
