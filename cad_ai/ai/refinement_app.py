import os
import cadquery as cq
import streamlit as st
import tempfile
import trimesh
from kronoslabs import KronosLabs

# ==============================
# 🔧 Setup
# ==============================
st.set_page_config(page_title="CAD AI Refinement", page_icon="🧠", layout="wide")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

API_KEY = os.getenv("KRONOS_API_KEY", "kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")
client = KronosLabs(api_key=API_KEY)

# session state
if "model" not in st.session_state:
    st.session_state.model = cq.Workplane("XY")
if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": "You are a CAD assistant that writes valid CadQuery code. \
Respond only with Python code using 'model = ...' or modifications to 'model'."}
    ]
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==============================
# 🧩 Helper functions
# ==============================
def apply_cad_code(code_snippet):
    """Execute AI-generated CadQuery code."""
    try:
        exec(code_snippet, {"cq": cq, "model": st.session_state.model})
        st.success("✅ Successfully applied AI update.")
    except Exception as e:
        st.error(f"❌ Error: {e}")

def export_and_preview(model):
    """Export current model and display 3D view."""
    tmp_path = os.path.join(MODELS_DIR, "temp.stl")
    cq.exporters.export(model, tmp_path)
    mesh = trimesh.load(tmp_path)
    st.session_state.preview_html = mesh.scene().save_as_html()
    return tmp_path

# ==============================
# 🖥️ UI
# ==============================
st.title("🧠 CAD AI Refinement Chat")
st.caption("Talk to your CAD assistant — generate and refine 3D models in real time.")

cols = st.columns([2, 3])

with cols[0]:
    st.subheader("💬 Chat with AI")
    user_input = st.text_input("Type a design command:", placeholder="e.g. create a 40x20x5 plate with a 10mm hole")

    if st.button("Send", use_container_width=True) and user_input:
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.messages.append(("🧠 You", user_input))

        # Send to KronosLabs
        response = client.chat.completions.create(
            messages=st.session_state.history,
            model="hermes",
            temperature=0.3,
            is_stream=False
        )   

        ai_message = response.choices[0].message.content
        st.session_state.messages.append(("🤖 AI", ai_message))
        st.session_state.history.append({"role": "assistant", "content": ai_message})

        # Execute returned code
        apply_cad_code(ai_message)

        # Update preview
        export_and_preview(st.session_state.model)

    # display conversation
    for sender, msg in st.session_state.messages[::-1]:
        st.markdown(f"**{sender}:** {msg}")

    if st.button("💾 Export STL", use_container_width=True):
        export_path = os.path.join(MODELS_DIR, "exported_model.stl")
        cq.exporters.export(st.session_state.model, export_path)
        st.download_button("Download STL", open(export_path, "rb"), file_name="model.stl")

with cols[1]:
    st.subheader("🧱 Model Preview")
    if "preview_html" in st.session_state:
        st.components.v1.html(st.session_state.preview_html, height=600)
    else:
        st.info("Generate something to preview it here.")
