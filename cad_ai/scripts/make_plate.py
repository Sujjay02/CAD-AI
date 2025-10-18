import cadquery as cq
import os

# --- setup paths ---
# get the folder this script lives in
base_dir = os.path.dirname(__file__)
# move one level up to /cad_ai
root_dir = os.path.abspath(os.path.join(base_dir, ".."))
# create /models if it doesn't exist
output_dir = os.path.join(root_dir, "models")
os.makedirs(output_dir, exist_ok=True)

# --- make a simple plate ---
plate = (
    cq.Workplane("XY")
    .box(10, 20, 2)                     # basic rectangular plate
    .faces(">Z").workplane()            # select the top face
    .hole(5)                            # drill a 5mm hole
)

# --- export the result ---
output_file = os.path.join(output_dir, "plate_10x20.stl")
cq.exporters.export(plate, output_file)

print(f"✅ Exported model to: {output_file}")
