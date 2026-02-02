import adsk.core, adsk.fusion, adsk.cam, traceback
import json
import sys

# Arguments: f3d file path, output json path
f3d_path = sys.argv[1]
json_path = sys.argv[2]

app = adsk.core.Application.get()
ui = app.userInterface

try:
    # Open document
    doc = app.documents.open(f3d_path)
    design = adsk.fusion.Design.cast(app.activeProduct)

    model_data = {
        "file_name": f3d_path,
        "bodies": [],
        "material": None,
        "total_volume": 0
    }

    # Read material if set
    if design.materials.count > 0:
        model_data["material"] = design.materials.item(0).name

    # Iterate all components
    for comp in design.allComponents:
        for body in comp.bRepBodies:
            body_info = {
                "name": body.name,
                "volume": body.volume,
                "bounding_box": [
                    body.boundingBox.maxPoint.x - body.boundingBox.minPoint.x,
                    body.boundingBox.maxPoint.y - body.boundingBox.minPoint.y,
                    body.boundingBox.maxPoint.z - body.boundingBox.minPoint.z
                ]
            }
            model_data["bodies"].append(body_info)
            model_data["total_volume"] += body.volume

    # Write JSON
    with open(json_path, "w") as f:
        json.dump(model_data, f, indent=4)

    doc.close(False)

except:
    if ui:
        ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
