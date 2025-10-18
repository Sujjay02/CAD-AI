import streamlit as st
import os
import re
import cadquery as cq
import tempfile
from kronoslabs import KronosLabs

# === PATHS ===
BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# === KRONOS CLIENT ===
client = KronosLabs(api_key="kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")  # <--- replace this

# === HELPERS ===
def prompt_to_filename(prompt: str) -> str:
    """Convert natural-language prompt into safe STL filename."""
    name = re.sub(r"[^a-zA-Z0-9]+", "_", prompt.lower()).strip("_")
    return f"{name[:40] or 'model'}.stl"


def safe_exec(code: str):
    """Run CadQuery code and return the first Workplane object."""
    local_vars = {}
    try:
        exec(code, {"cq": cq}, local_vars)
        for v in local_vars.values():
            if isinstance(v, cq.Workplane):
                return v
    except Exception as e:
        st.error(f"❌ Error executing generated code:\n\n{e}")
    return None


def export_and_embed(model, filename):
    """Export STL and embed it in a model-viewer served by Streamlit."""
    # Save STL to the /models directory
    stl_path = os.path.join(MODELS_DIR, filename)
    cq.exporters.export(model, stl_path)

    # Reopen and read the file so Streamlit can serve it via HTTP
    with open(stl_path, "rb") as f:
        st.session_state.stl_data = f.read()

    # Generate an HTML component for 3D preview using the data URI
    import base64
    stl_base64 = base64.b64encode(st.session_state.stl_data).decode("utf-8")

    html = f"""
    <model-viewer src="data:model/stl;base64,{stl_base64}"
                  alt="3D preview"
                  auto-rotate
                  camera-controls
                  background-color="#f0f0f0"
                  style="width:100%;height:600px;">
    </model-viewer>
    <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
    """

    st.session_state.preview_html = html
    st.session_state.exported_file = stl_path
    return stl_path


# === STREAMLIT UI ===
st.title("🧠 CAD AI — STL Generator with 3D Preview")

prompt = st.text_area("Describe your 3D model:", height=100)
generate = st.button("⚙️ Generate and Preview")

if generate:
    with st.spinner("🧩 AI is generating your model..."):
        try:
            response = client.chat.completions.create(
                prompt=(
                    f"Write a CadQuery Python script that creates this model: {prompt}. "
                    f"Define it as `model = cq.Workplane('XY')...` and nothing else."
                ),
                model="hermes",
                temperature=0.4,
                is_stream=False,
            )

            ai_code = response.choices[0].message.content
            st.code(ai_code, language="python")

            model = safe_exec(ai_code)
            if model:
                filename = prompt_to_filename(prompt)
                export_and_embed(model, filename)
                st.success(f"✅ Model saved as `{filename}`.")
            else:
                st.error("⚠️ The AI didn’t produce a valid CadQuery model.")
        except Exception as e:
            st.error(f"Error: {e}")

# === 3D PREVIEW + DOWNLOAD ===
if "preview_html" in st.session_state:
    st.subheader("🧩 3D Preview")
    st.components.v1.html(st.session_state.preview_html, height=600)

if "exported_file" in st.session_state and os.path.exists(st.session_state.exported_file):
    with open(st.session_state.exported_file, "rb") as f:
        st.download_button(
            label="⬇️ Download STL",
            data=f,
            file_name=os.path.basename(st.session_state.exported_file),
            mime="application/sla",
        )
