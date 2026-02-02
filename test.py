import requests

file_path = r"C:\Users\jdwil\Documents\Projects\GTC 2026 Golden Ticket\Headphone hanger.f3d"

with open(file_path, "rb") as f:
    files = {"file": ("Headphone hanger.f3d", f, "application/octet-stream")}
    response = requests.post("http://127.0.0.1:8000/upload-f3d/", files=files)

print("Status code:", response.status_code)
print("Response text:", response.text)