import os
import streamlit as st
import cadquery as cq
import trimesh
from kronoslabs import KronosLabs

# -------------------------------
# 📦 Setup
# -------------------------------
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

client = KronosLabs(api_key="your-kronoslabs-api-key-here")

# -------------------------------
# ⚙️ Model export & preview
# -------------------------------
def export_and_preview(model):
    """Export current model and display 3D view."""
    tmp_path = os.path.join(MODELS_DIR, "temp.stl")
    cq.exporters.export(model, tmp_path)

    mesh = trimesh.load(tmp_path)

    # Wrap into a Scene if needed
    if isinstance(mesh, trimesh.Trimesh):
        scene = trimesh.Scene(mesh)
    else:
        scene = mesh

    # Use correct HTML export method
    if hasattr(scene, "to_html"):
        st.session_state.preview_html = scene.to_html()
    else:
        st.session_state.preview_html = "<p>3D preview not supported in this trimesh version.</p>"

    return tmp_path

# -------------------------------
# 💬 Kronos AI interaction
# -------------------------------
def ai_refine(prompt):
    """Send current user prompt to KronosLabs AI."""
    try:
        response = client.chat.completions.create(
            model="hermes",
            prompt=prompt,
            temperature=0.7,
            is_stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"AI request failed: {e}")
        return None

# -------------------------------
# 🚀 Streamlit UI
# -------------------------------
st.set_page_config(page_title="CAD Refinement AI", layout="wide")

st.title("🤖 CAD Refinement Assistant")
st.write("Use natural language to refine your 3D model interactively.")

if "model" not in st.session_state:
    st.session_state.model = cq.Workplane("XY").box(10, 10, 10)
    export_and_preview(st.session_state.model)

if "history" not in st.session_state:
    st.session_state.history = []

# 3D Preview Panel
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("3D Preview")
    st.components.v1.html(st.session_state.preview_html, height=600)

with col2:
    st.subheader("AI Refinement")
    user_prompt = st.text_area("Describe how to change the model:", height=150)
    if st.button("Refine Model"):
        if user_prompt.strip():
            st.session_state.history.append({"role": "user", "content": user_prompt})

            with st.spinner("Refining with Kronos AI..."):
                ai_response = ai_refine(user_prompt)
                if ai_response:
                    st.session_state.history.append({"role": "assistant", "content": ai_response})
                    st.success("✅ Model refinement complete!")
                    # TODO: Add code execution of AI's CAD edits here (Phase 5)
        else:
            st.warning("Please enter a prompt first.")

st.divider()
st.subheader("Conversation Log")

for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**🧑 You:** {msg['content']}")
    else:
        st.markdown(f"**🤖 AI:** {msg['content']}")
