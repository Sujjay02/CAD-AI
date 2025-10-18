import streamlit as st
import os
import cadquery as cq
import trimesh
from kronoslabs import KronosLabs

# === PATH SETUP ===
BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# === AI CLIENT ===
client = KronosLabs(api_key="kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")  # replace with your key

# === UTILS ===
def export_and_preview(model):
    """Export current model and generate best-possible preview."""
    tmp_path = os.path.join(MODELS_DIR, "temp.stl")
    cq.exporters.export(model, tmp_path)
    mesh = trimesh.load(tmp_path)

    # Make sure we have a Scene object
    scene = trimesh.Scene(mesh) if isinstance(mesh, trimesh.Trimesh) else mesh

    # Try multiple preview methods
    html_preview = None

    # Try to_html() (newer versions)
    if hasattr(scene, "to_html"):
        try:
            html_preview = scene.to_html()
        except Exception as e:
            print(f"[WARN] to_html() failed: {e}")

    # Try show() (interactive fallback)
    if html_preview is None and hasattr(scene, "show"):
        try:
            html_preview = scene.show(jupyter=False)
        except Exception as e:
            print(f"[WARN] show() failed: {e}")

    # Last resort: basic HTML viewer
    if html_preview is None:
        stl_url = f"file://{tmp_path}"
        html_preview = f"""
        <html>
        <body style='margin:0;padding:0;'>
            <model-viewer src="{stl_url}" auto-rotate camera-controls style="width:100%;height:600px;"></model-viewer>
            <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
        </body>
        </html>
        """

    st.session_state.preview_html = html_preview
    return tmp_path


# === STREAMLIT UI ===
st.title("🧠 CAD AI — Model Refinement Assistant")

if "history" not in st.session_state:
    st.session_state.history = []
if "model" not in st.session_state:
    st.session_state.model = (
        cq.Workplane("XY").box(10, 20, 2).faces(">Z").workplane().hole(5)
    )
    export_and_preview(st.session_state.model)

# --- USER INPUT ---
user_prompt = st.text_area("Describe a change to make:", height=100)

if st.button("💬 Ask AI to Modify"):
    with st.spinner("Thinking..."):
        try:
            response = client.chat.completions.create(
                prompt=f"Modify the CAD model based on: {user_prompt}",
                model="hermes",
                temperature=0.7,
                is_stream=False,
            )
            result_text = response.choices[0].message.content
            st.session_state.history.append({"role": "assistant", "content": result_text})
            st.success("✅ AI processed your request!")

            # Example placeholder for model refinement (customize as needed)
            st.session_state.model = cq.Workplane("XY").box(10, 20, 2)
            export_and_preview(st.session_state.model)

        except Exception as e:
            st.error(f"Error communicating with KronosLabs API: {e}")

# --- SHOW 3D MODEL ---
st.subheader("🧩 Model Preview")
st.components.v1.html(st.session_state.preview_html, height=600)
