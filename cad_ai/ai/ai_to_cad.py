import os
import cadquery as cq
from kronoslabs import KronosLabs

# Initialize AI client
client = KronosLabs(api_key="kl_ee83673ca58773041338f9db70d600e0d6f6c6124e71cdff15728f62b9c3417a")  # 🔒 plug in your key here

# --- setup paths ---
base_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(base_dir, ".."))
output_dir = os.path.join(root_dir, "models")
os.makedirs(output_dir, exist_ok=True)

def ai_to_cad(prompt: str):
    """
    Convert a text command into a CadQuery model via KronosLabs Hermes model.
    """

    print(f"🧠 AI prompt: {prompt}")

    response = client.chat.completions.create(
        prompt=f"You are an assistant that writes CadQuery Python code to make 3D parts. Make approximations of measurements if not specified. The stl file has to be called ai_generated_part.stl"
               f"Respond with ONLY executable CadQuery Python code (no explanation)."
               f"Example: cq.Workplane('XY').box(10,20,2).faces('>Z').workplane().hole(5) "
               f"Now make a model based on this description: {prompt}",
        model="hermes",
        temperature=0.4,
        is_stream=False
    )

    code = response.choices[0].message.content.strip()
    print(f"\n🤖 Generated code:\n{code}\n")

    # Safely execute the generated CadQuery code
    try:
        result = eval(code)
    except Exception as e:
        print(f"❌ Error executing AI-generated code: {e}")
        return

    
    # Export the model
    output_path = os.path.join(output_dir, "ai_generated_part.stl")
    cq.exporters.export(result, output_path)
    print(f"✅ Exported AI-generated model to: {output_path}")

    return result


# --- test run ---
if __name__ == "__main__":
    user_prompt = input("🗣️ Describe the part you want to make: ")
    ai_to_cad(user_prompt)
