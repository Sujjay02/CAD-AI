import os
import sys
import importlib.util
from kronoslabs import KronosLabs
import cadquery as cq

# ---------------- SETUP ----------------


client = KronosLabs(api_key="kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")
base_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(base_dir, ".."))
models_dir = os.path.join(root_dir, "models")
os.makedirs(models_dir, exist_ok=True)

# --------------------------------------
def generate_cad_code(prompt: str) -> str:
    """
    Ask KronosLabs Hermes model for valid CadQuery code.
    """
    system_prompt = (
        "You are a CAD code generator using CadQuery. "
        "Output only executable Python code that builds a 3D model "
        "matching the user request and saves it to variable `model`."
    )

    response = client.chat.completions.create(
        prompt=f"{system_prompt}\nUser: {prompt}",
        model="hermes",
        temperature=0.3,
        is_stream=False
    )

    code = response.choices[0].message.content.strip()
    # optional safety filter
    if "import os" in code or "open(" in code:
        raise ValueError("Unsafe code detected.")
    return code


def run_cad_code(code: str, filename="ai_model.stl"):
    """
    Execute the CadQuery code string, export the resulting model.
    """
    namespace = {"cq": cq}
    exec(code, namespace)

    model = namespace.get("model")
    if model is None:
        raise RuntimeError("No model variable found in generated code.")

    out_path = os.path.join(models_dir, filename)
    cq.exporters.export(model, out_path)
    print(f"✅ Model exported to: {out_path}")
    return model


def main():
    if len(sys.argv) < 2:
        print("Usage: python chat_interface.py \"make a cube with a hole\"")
        sys.exit(1)

    user_prompt = sys.argv[1]
    print(f"🧠 Generating model for: {user_prompt}")

    code = generate_cad_code(user_prompt)
    print("----------- Generated CadQuery code -----------")
    print(code)
    print("------------------------------------------------")

    try:
        model = run_cad_code(code)
        
    except Exception as e:
        print(f"❌ Error executing model: {e}")


if __name__ == "__main__":
    main()
