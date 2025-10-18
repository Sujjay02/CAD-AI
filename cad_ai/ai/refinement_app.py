import streamlit as st
import os
import re
import cadquery as cq
import trimesh
from kronoslabs import KronosLabs

# === PATHS ===
BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# === KRONOS CLIENT ===
client = KronosLabs(api_key="kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")  # 🔑 plug in your key

# === UTILITIES ===
def prompt_to_filename(prompt: str) -> str:
    """Convert a text prompt into a short filesystem-safe STL file name."""
    name = re.sub(r"[^a-zA-Z0-9]+", "_", prompt.lower()).strip("_")
    if len(name) > 40:
        name = name[:40]
    return f"{name or 'model'}.stl"


def safe_exec(code: str):
    """Safely execute CadQuery code and return model object if created."""
    local_vars = {}
    try:
        exec(code, {"cq": cq}, local_vars)
        for v in local_vars.values():
            if isinstance(v, cq.Workplane):
                return v
    except Exception as e:
        st.error(f"❌ Error in generated code: {e}")
    return None


def export_and_preview(model, filename):
    """Export model to STL, preview it, and store path in session."""
    stl_path = os.path.join(MODELS_DIR, filename)
    cq.exporters.export(model, stl_path)
    mesh = trimesh.load(stl_path)
    scene = trimesh.Scene(mesh) if isinstance(mesh, trimesh.Trimesh) else mesh

    if hasattr(scene, "to_html"):
        html = scene.to_html()
    elif hasattr(scene, "show"):
        html = scene.show(jupyter=False)
    else:
        stl_url = f"file://{stl_path}"
        html = f"""
        <model-viewer src="{stl_url}" auto-rotate camera-controls style="width:100%;height:600px;"></model-viewer>
        <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
        """

    st.session_state.preview_html = html
    st.session_state.exported_file = stl_path
    return stl_path


# === STREAMLIT UI ===
st.title("🧠 CAD AI — STL Model Generator (Auto-Naming Edition)")

prompt = st.text_area("Describe your 3D model:", height=100)
generate = st.button("⚙️ Generate and Save Model")

if generate:
    with st.spinner("🧩 Generating model from AI..."):
        try:
            response = client.chat.completions.create(
                prompt=(
                    f"Write a valid CadQuery script to create this model: {prompt}\n"
                    f"Only output Python code. Define a variable named 'model' "
                    f"as a cq.Workplane object. Example:\n"
                    f"model = cq.Workplane('XY').box(10,10,10)"
                ),
                model="hermes",
                temperature=0.4,
                is_stream=False,
            )

            ai_code = response.choices[0].message.content
            st.code(ai_code, language="python")

            model = safe_exec(ai_code)
            if model:
                file_name = prompt_to_filename(prompt)
                file_path = export_and_preview(model, file_name)
                st.success(f"✅ Model saved as: {file_name}")
            else:
                st.error("⚠️ AI didn't produce a valid CadQuery model.")
        except Exception as e:
            st.error(f"Error: {e}")

# === PREVIEW + DOWNLOAD ===
if "preview_html" in st.session_state:
    st.subheader("🧩 3D Preview")
    st.components.v1.html(st.session_state.preview_html, height=600)

if "exported_file" in st.session_state and os.path.exists(st.session_state.exported_file):
    with open(st.session_state.exported_file, "rb") as f:
        st.download_button(
            label="⬇️ Download STL File",
            data=f,
            file_name=os.path.basename(st.session_state.exported_file),
            mime="application/sla",
        )
