from fastapi import FastAPI, UploadFile
import shutil
import subprocess
import os

app = FastAPI()


@app.post("/upload-f3d/")
async def upload_f3d(file: UploadFile):
    try:
        # Save uploaded .f3d file
        f3d_path = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        with open(f3d_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run Fusion 360 Python script to export JSON summary
        # Replace with path to your Fusion 360 Python script
        fusion_script_path = "fusion_export_json.py"
        json_output_path = f"temp/{file.filename}.json"
        fusion_exe_path = r"C:\Users\jdwil\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Autodesk\Autodesk Fusion.lnk"

        # Run script via command line (Fusion 360 must allow this)
        subprocess.run([
            fusion_exe_path,  # Fusion 360 Python executable / command
            "/script",
            fusion_script_path,
            f3d_path,
            json_output_path
        ], check=True)

        # Read JSON and return to frontend or Nemotron
        with open(json_output_path, "r") as f:
            model_json = f.read()

        return {"model_json": model_json}


    except Exception as e:
        return {"error": str(e)}