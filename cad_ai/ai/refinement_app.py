import streamlit as st
import os
import cadquery as cq
import trimesh
from kronoslabs import KronosLabs

# === PATHS ===
BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# === KRONOS CLIENT ===
client = KronosLabs(api_key="kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")  # replace with your key

# === UTILITIES ===
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


def export_and_preview(model):
    """Export current model and show preview."""
    tmp_path = os.path.join(MODELS_DIR, "ai_generated.stl")
    cq.exporters.export(model, tmp_path)
    mesh = trimesh.load(tmp_path)
    scene = trimesh.Scene(mesh) if isinstance(mesh, trimesh.Trimesh) else mesh

    # Try to preview using to_html, show, or fallback
    if hasattr(scene, "to_html"):
        html = scene.to_html()
    elif hasattr(scene, "show"):
        html = scene.show(jupyter=False)
    else:
        stl_url = f"file://{tmp_path}"
        html = f"""
        <model-viewer src="{stl_url}" auto-rotate camera-controls style="width:100%;height:600px;"></model-viewer>
        <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
        """
    st.session_state.preview_html = html


# === STREAMLIT UI ===
st.title("🧠 CAD AI — Model Generator")

prompt = st.text_area("Describe the 3D model you want to generate:", height=100)
generate = st.button("⚙️ Generate Model")

if generate:
    with st.spinner("Asking AI to create your model..."):
        try:
            response = client.chat.completions.create(
                prompt=f"Write a valid CadQuery script to generate this model: {prompt}\n"
                       f"Only output Python code that defines a variable called model "
                       f"as a cq.Workplane object. Example: model = cq.Workplane('XY').box(10,10,10)",
                model="hermes",
                temperature=0.4,
                is_stream=False,
            )

            ai_code = response.choices[0].message.content
            st.code(ai_code, language="python")

            model = safe_exec(ai_code)

            if model:
                export_and_preview(model)
                st.success("✅ Model generated successfully!")
            else:
                st.error("⚠️ AI didn't produce a valid CadQuery model.")

        except Exception as e:
            st.error(f"API error: {e}")

# === PREVIEW ===
if "preview_html" in st.session_state:
    st.components.v1.html(st.session_state.preview_html, height=600)
