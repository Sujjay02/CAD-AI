import streamlit as st
import os, re, json, base64
from datetime import datetime
import cadquery as cq
import streamlit.components.v1 as components
from kronoslabs import KronosLabs

# === PATH SETUP ===
BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(MODELS_DIR, "history.json")

# === KRONOS CLIENT ===
client = KronosLabs(api_key="kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")

# === HELPERS ===
def prompt_to_filename(prompt: str) -> str:
    """Make a filename-safe version of the user's text."""
    name = re.sub(r"[^a-zA-Z0-9]+", "_", prompt.lower()).strip("_")
    return f"{name[:40] or 'model'}.stl"

def clean_ai_output(raw_text: str) -> str:
    """Remove markdown fences and stray commentary from AI code."""
    code = re.sub(r"^```[a-zA-Z]*|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return code

def validate_code(code: str) -> bool:
    """Check if Python code compiles cleanly."""
    try:
        compile(code, "<string>", "exec")
        return True
    except SyntaxError as e:
        st.error(f"⚠️ Syntax error: {e}")
        return False

def safe_exec(code: str):
    """Execute CadQuery code safely and return the model."""
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
    """Export CadQuery model to STL and return (path, base64)."""
    path = os.path.join(MODELS_DIR, filename)
    cq.exporters.export(model, path)
    with open(path, "rb") as f:
        data = f.read()
    return path, base64.b64encode(data).decode("utf-8")

def make_html_viewer(stl_b64, height=600):
    """Render STL with model-viewer."""
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

# === STREAMLIT UI ===
st.set_page_config(page_title="CADgpt", layout="wide")

# --- Tweak sidebar margins ---
st.markdown(
    """
    <style>
        /* Reduce padding around the sidebar */
        [data-testid="stSidebar"] {
            padding-top: 0.5rem;
            padding-right: 0.5rem;
            padding-left: 0.5rem;
        }

        /* Tighten up header and text spacing */
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] p {
            margin-top: 0.3rem;
            margin-bottom: 0.3rem;
        }

        /* Compress the space between history items */
        .stMarkdown {
            margin-bottom: 0.02rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)



st.title("🧠 CADgpt")

if "history" not in st.session_state:
    st.session_state.history = load_history()

# === SIDEBAR GALLERY ===
st.sidebar.header("📂 Model History")
for i, h in enumerate(reversed(st.session_state.history)):
    st.sidebar.markdown(f"**{h['prompt']}**  \n_{h['timestamp'][:19]}_")
    with st.sidebar:
        components.html(make_html_viewer(h["stl_b64"], height=150), height=170)
    if st.sidebar.button(f"🧩 Load {h['filename']}", key=f"load_{i}"):
        st.session_state.preview_html = make_html_viewer(h["stl_b64"])
        st.session_state.exported_file = h["path"]
        st.session_state.last_code = h["code"]
        st.session_state.last_prompt = h["prompt"]

# === MAIN UI ===
st.subheader("🧠 CAD Model Generator")

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    prompt = st.text_area(
        "Describe your 3D model:",
        value=st.session_state.get("last_prompt", ""),
        height=100
    )

with col2:
    # 🆕 New Chat button — resets the current session state
    if st.button("🆕 New Chat", use_container_width=True):
        for key in [
            "preview_html",
            "exported_file",
            "last_code",
            "last_prompt"
        ]:
            st.session_state.pop(key, None)
        st.success("✨ New chat started — workspace cleared.")
        st.rerun()

with col3:
    # 🧹 Clear History button — deletes all stored models
    if st.button("🧹 Clear History", use_container_width=True):
        confirm = st.warning("⚠️ This will delete all saved models. Click again to confirm.")
        if st.button("Confirm Delete", use_container_width=True, key="confirm_clear"):
            try:
                st.session_state.history = []
                if os.path.exists(HISTORY_FILE):
                    os.remove(HISTORY_FILE)
                for f in os.listdir(MODELS_DIR):
                    if f.endswith(".stl"):
                        os.remove(os.path.join(MODELS_DIR, f))
                st.success("🧹 All model history cleared.")
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing history: {e}")

generate = st.button("⚙️ Generate Fresh Model")




refine_prompt = st.text_input("🔁 Refine last model (describe change):", placeholder="e.g. make the base thicker")
refine = st.button("✏️ Apply Refinement")

def run_and_display(ai_code, prompt):
    if not validate_code(ai_code):
        return
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

# === GENERATE NEW MODEL ===
if generate:
    with st.spinner("🎨 Creating model..."):
        try:
            response = client.chat.completions.create(
                prompt=f"Write only valid CadQuery Python code that defines a model using cq.Workplane('XY'). "
                       f"No markdown or text, only executable code. Task: {prompt}",
                model="hermes",
                temperature=0.4,
                is_stream=False,
            )
            ai_code = clean_ai_output(response.choices[0].message.content)
            st.text_area("🧩 AI Raw Code", value=ai_code, height=200)
            st.session_state.last_code = ai_code
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
            refined_code = clean_ai_output(response.choices[0].message.content)
            st.text_area("🧩 Refined AI Code", value=refined_code, height=200)
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
