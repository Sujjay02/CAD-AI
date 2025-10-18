import streamlit as st
import os, re, json, base64
from datetime import datetime
import cadquery as cq
from kronoslabs import KronosLabs

# === PATHS ===
BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(MODELS_DIR, "history.json")

# === KRONOS CLIENT ===
client = KronosLabs(api_key="kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")

# === HELPERS ===
def prompt_to_filename(prompt: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]+", "_", prompt.lower()).strip("_")
    return f"{name[:40] or 'model'}.stl"

def safe_exec(code: str):
    local_vars = {}
    try:
        exec(code, {"cq": cq}, local_vars)
        for v in local_vars.values():
            if isinstance(v, cq.Workplane):
                return v
    except Exception as e:
        st.error(f"❌ Execution error:\n{e}")
    return None

def export_stl(model, filename):
    path = os.path.join(MODELS_DIR, filename)
    cq.exporters.export(model, path)
    with open(path, "rb") as f:
        data = f.read()
    return path, base64.b64encode(data).decode("utf-8")

def make_html_viewer(stl_b64, height=600):
    return f"""
    <model-viewer src="data:model/stl;base64,{stl_b64}"
        alt="3D Preview"
        auto-rotate camera-controls
        background-color="#f0f0f0"
        style="width:100%;height:{height}px;">
    </model-viewer>
    <script type="module"
        src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
    """

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# === INIT ===
st.set_page_config(page_title="CAD AI", layout="wide")
st.title("🧠 CAD AI — Refinement Chain Mode")

if "history" not in st.session_state:
    st.session_state.history = load_history()

# === SIDEBAR GALLERY ===
st.sidebar.header("📂 Model History")
for i, h in enumerate(reversed(st.session_state.history)):
    st.sidebar.markdown(f"**{h['prompt']}**  \n_{h['timestamp'][:19]}_")
    st.sidebar.components.v1.html(make_html_viewer(h["stl_b64"], height=150), height=170)
    if st.sidebar.button(f"🧩 Load {h['filename']}", key=f"load_{i}"):
        st.session_state.preview_html = make_html_viewer(h["stl_b64"])
        st.session_state.exported_file = h["path"]
        st.session_state.last_code = h["code"]
        st.session_state.last_prompt = h["prompt"]

# === MAIN AREA ===
prompt = st.text_area("Describe your 3D model:", value=st.session_state.get("last_prompt", ""), height=100)
generate = st.button("⚙️ Generate Fresh Model")

refine_prompt = st.text_input("🔁 Refine last model (describe change):", placeholder="e.g. make the base thicker")
refine = st.button("✏️ Apply Refinement")

def run_and_display(ai_code, prompt):
    model = safe_exec(ai_code)
    if model:
        filename = prompt_to_filename(prompt)
        path, stl_b64 = export_stl(model, filename)
        html = make_html_viewer(stl_b64)
        st.session_state.preview_html = html
        st.session_state.exported_file = path
        st.session_state.last_prompt = prompt
        entry = {
            "prompt": prompt,
            "filename": filename,
            "path": path,
            "code": ai_code,
            "stl_b64": stl_b64,
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.history.append(entry)
        save_history(st.session_state.history)
        st.success(f"✅ Saved `{filename}`.")
    else:
        st.error("⚠️ Invalid CadQuery code.")

# === GENERATE NEW ===
if generate:
    with st.spinner("🎨 Creating model..."):
        try:
            response = client.chat.completions.create(
                prompt=f"Write a full CadQuery Python script that builds this model: {prompt}. Use `model = cq.Workplane('XY')...` only.",
                model="hermes",
                temperature=0.4,
                is_stream=False,
            )
            ai_code = response.choices[0].message.content
            st.session_state.last_code = ai_code
            st.code(ai_code, language="python")
            run_and_display(ai_code, prompt)
        except Exception as e:
            st.error(f"Error: {e}")

# === REFINEMENT ===
if refine and "last_code" in st.session_state:
    with st.spinner("✏️ Refining model..."):
        try:
            old_code = st.session_state.last_code
            edit_instruction = f"Modify this CadQuery script to {refine_prompt}. Keep all context and variable names the same."
            response = client.chat.completions.create(
                prompt=f"{edit_instruction}\n\nExisting code:\n{old_code}",
                model="hermes",
                temperature=0.5,
                is_stream=False,
            )
            refined_code = response.choices[0].message.content
            st.code(refined_code, language="python")
            run_and_display(refined_code, f"{st.session_state.last_prompt} → refined: {refine_prompt}")
            st.session_state.last_code = refined_code
        except Exception as e:
            st.error(f"Error refining: {e}")

# === PREVIEW & DOWNLOAD ===
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
