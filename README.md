# InteliCAD

An AI-driven CAD design automation system that uses NVIDIA's Nemotron LLM to interpret natural language design commands and automatically execute modifications to Autodesk Fusion 360 models.

---

## How It Works

InteliCAD runs a three-phase AI pipeline to turn a plain-English instruction like *"make this lighter without compromising structural integrity"* into executed CAD operations inside Fusion 360.

**Phase 1 — Design Intent Analysis**
The backend sends the user's command to Nemotron, which analyzes the design goal, infers constraints (load-bearing, decorative, enclosure, etc.), and produces a structured modification strategy.

**Phase 2 — CAD Operation Generation**
Using the strategy from Phase 1 and real model data (mass, volume, bounding box, features) collected by the Fusion add-in, Nemotron generates a list of validated, parameter-safe CAD operations to execute.

**Phase 3 — Intelligent Retry**
If any operations fail during execution, the backend sends the failure details back to Nemotron, which diagnoses the cause and generates adjusted retry operations with corrected parameters.

---

## Architecture

```
User
 └─ POST /submit-job/  (CAD file + command)
        │
FastAPI Backend (fastUpload.py)
 ├─ Phase 1: Nemotron analyzes design intent
 └─ Phase 2a: Nemotron generates preliminary operations
        │
Fusion 360 Add-In (polls /poll-jobs/ every 10s)
 ├─ Analyzes active design  →  POST /jobs/{id}/analysis
        │
FastAPI Backend
 └─ Phase 2b: Nemotron refines operations using real model data
        │
Fusion 360 Add-In
 ├─ Executes each CAD operation via Fusion 360 API
 ├─ POST /complete-job/{id}  (uploads result .f3d)
 └─ POST /retry-failed/{id}  (if failures occurred)
        │
FastAPI Backend
 └─ Phase 3 (if needed): Nemotron adjusts failed operation params
        │
Fusion 360 Add-In  →  executes retry operations  →  uploads final result
        │
User
 └─ GET /download/{id}  (downloads completed .f3d)
```

---

## Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| Web framework | **FastAPI** |
| ASGI server | **Uvicorn** |
| Async HTTP client | **httpx** (NVIDIA API calls) |
| HTTP client (scripts) | **requests** |
| File uploads | **python-multipart** |
| Language | **Python 3.10+** |

### AI / LLM
| Role | Model |
|------|-------|
| Design intent & retry reasoning | **NVIDIA Nemotron** (`llama-3.3-nemotron-super-49b-v1.5`) |
| Fast structured JSON generation | **Meta Llama** (`llama-3.1-8b-instruct`) |
| API provider | **NVIDIA Build API** (`integrate.api.nvidia.com`) |

### CAD Integration
| Layer | Technology |
|-------|-----------|
| CAD platform | **Autodesk Fusion 360** |
| Add-in runtime | **Fusion 360 Add-In API** (`adsk.core`, `adsk.fusion`) |
| Add-in HTTP comms | Python **stdlib** only (`urllib`) — no pip packages allowed inside Fusion |

### Data & Storage
| Concern | Approach |
|---------|---------|
| Job state | In-memory dict (no database) |
| File storage | Local filesystem (`jobs/` directory) |
| CAD file format | Fusion Archive (`.f3d`) |
| Data exchange | JSON (operations, model analysis, AI responses) |

### Developer Tooling
| Tool | Purpose |
|------|---------|
| Git / GitHub | Version control |
| `simulation.py` | Local test harness mimicking the Fusion add-in |
| `Fusion_AddIn.py` | One-command add-in installer |
| `update_addin.py` | Push code changes to the installed add-in |
| `Test & Diagnostic Scripts/` | API tests, status checks, job inspection |

### Platform
| | |
|--|--|
| OS | **Windows** (Fusion 360 requirement; paths target `C:\Users\...`) |
| Python environment | **venv** |

---

## Project Structure

```
GTC 2026 Golden Ticket/
├── fusion_AddIn/
│   ├── InteliCAD.py          # Add-in entry point; polling loop and job dispatch
│   ├── api_client.py         # HTTP client (stdlib only) for add-in ↔ backend comms
│   ├── model_analyzer.py     # Extracts mass, volume, bounding box, features from active design
│   ├── operation_executor.py # Executes CAD operations via Fusion 360 API
│   └── InteliCAD.manifest    # Fusion 360 add-in manifest
│
├── fastUpload.py             # FastAPI backend — orchestrates the full AI pipeline
├── simulation.py             # Local simulator that mimics the Fusion add-in (no Fusion needed)
├── Fusion_AddIn.py           # Interactive installer: copies add-in files into Fusion's add-ins folder
├── update_addin.py           # Utility to re-copy updated add-in files without reinstalling
├── fusion_export_json.py     # Standalone Fusion script to export model data as JSON
│
├── Test & Diagnostic Scripts/
│   ├── test.py               # Submit a test job to the backend
│   ├── complex_nvidia_test.py # Test Phase 1 design intent analysis with complex commands
│   ├── nvidia_test.py        # Test NVIDIA API connectivity and model availability
│   ├── test_operations_direct.py # Run CAD operations directly inside Fusion 360
│   ├── check_operations.py   # Report which operations are implemented vs. placeholder
│   ├── check_status.py       # Check add-in log activity and backend connectivity
│   ├── check_version.py      # Detect which version of the add-in is installed
│   ├── job_check.py          # Verify completed jobs; show before/after file comparisons
│   └── inspect_job.py        # Inspect full details of a specific job
│
├── Headphone hanger.f3d      # Sample Fusion 360 model for testing
├── requirements.txt          # Python dependencies
└── .gitignore
```

---

## Prerequisites

- **Python 3.10+**
- **Autodesk Fusion 360** (required for real CAD execution; not needed for simulation/testing)
- **NVIDIA Build API key** — obtain one at [build.nvidia.com](https://build.nvidia.com)

---

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your NVIDIA API key

Open [fastUpload.py](fastUpload.py) and replace the placeholder value with your key:

```python
NVIDIA_API_KEY = "nvapi-YOUR_KEY_HERE"
```

---

## Running the Backend

```bash
uvicorn fastUpload:app --reload
```

The server starts at `http://127.0.0.1:8000`. Keep this running while using the add-in or simulator.

---

## Installing the Fusion 360 Add-In

Run the installer once to copy the add-in files into Fusion 360's add-ins directory:

```bash
python Fusion_AddIn.py
```

Then inside Fusion 360:

1. Open **Utilities → Add-Ins → Scripts and Add-Ins**
2. Under the **Add-Ins** tab, locate **InteliCAD**
3. Click **Run** (and optionally enable **Run on Startup**)

The add-in polls the backend every 10 seconds. Its activity is logged to `intelicad_log.txt` in the project root.

To push code changes to the installed add-in without re-running the installer:

```bash
python update_addin.py
```

---

## Testing Without Fusion 360

`simulation.py` mimics the add-in's polling and job-handling behavior using hardcoded model data, so you can test the full backend pipeline without Fusion open:

```bash
python simulation.py
```

---

## Submitting a Job

Use the `/submit-job/` endpoint to submit a CAD file and a design command:

```bash
curl -X POST http://127.0.0.1:8000/submit-job/ \
  -F "file=@Headphone hanger.f3d" \
  -F "command=Make this lighter without compromising structural integrity"
```

Check job status:

```bash
curl http://127.0.0.1:8000/job-status/{job_id}
```

Download the result:

```bash
curl -O http://127.0.0.1:8000/download/{job_id}
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/submit-job/` | Submit a `.f3d` file and design command |
| `GET` | `/poll-jobs/` | Add-in polls for pending jobs |
| `POST` | `/jobs/{job_id}/analysis` | Add-in submits model analysis data |
| `POST` | `/complete-job/{job_id}` | Add-in uploads the completed `.f3d` file |
| `POST` | `/retry-failed/{job_id}` | Request Phase 3 retry operations for failures |
| `GET` | `/job-status/{job_id}` | Check current status of a job |
| `GET` | `/download/{job_id}` | Download the completed result file |

---

## Implemented CAD Operations

| Operation | Status | Description |
|-----------|--------|-------------|
| `shell_body` | Implemented | Hollow out a solid to a specified wall thickness; opens the top face |
| `scale` | Implemented | Uniform scaling or independent per-axis (x/y/z) scaling |
| `fillet` / `fillet_edges` / `fillet_all_edges` | Implemented | Round all sharp (linear) edges to a given radius |
| `mirror` | Implemented | Mirror all bodies across the X, Y, or Z construction plane |
| `rotate` | Implemented | Rotate all bodies by angle (degrees) around X, Y, or Z axis |
| `move` | Implemented | Translate all bodies by x/y/z offset in mm |
| `add_ribs` | Implemented | Add a thin cross-brace rib via sketch extrude; sized to 30% of part |
| `strategic_holes` | Implemented | Cut a grid of holes through the top face for material/weight reduction |
| `add_ventilation` / `ventilation` | Implemented | Cut hexagonal or grid ventilation holes through the top face |
| `apply_draft_angles` / `draft_angles` | Implemented | Apply draft angles to vertical faces for mold/manufacturing compatibility |
| `variable_wall_thickness` / `variable_thickness` | Partial | Applies a uniform shell with top/bottom/side face classification; true per-face variable thickness not yet supported |
| `pattern` | Partial | Rectangular pattern only; circular and other pattern types not yet supported |
| `topology_optimization` / `run_topology_optimization` | Skipped | Requires Fusion Generative Design API; skips gracefully and suggests shell + ribs instead |
| `lattice_infill` | Skipped | Requires a mesh generation library; skips gracefully and suggests shell instead |

---

## Diagnostics

```bash
# Check which operations are implemented vs. placeholder
python "Test & Diagnostic Scripts/check_operations.py"

# Check add-in log activity and backend connectivity
python "Test & Diagnostic Scripts/check_status.py"

# Inspect details of a specific job
python "Test & Diagnostic Scripts/inspect_job.py" {job_id}

# Verify completed jobs and compare input/output files
python "Test & Diagnostic Scripts/job_check.py"

# Test NVIDIA API connectivity
python "Test & Diagnostic Scripts/nvidia_test.py"
```

---

## AI Models Used

| Model | Role |
|-------|------|
| `nvidia/llama-3.3-nemotron-super-49b-v1.5` | Phase 1 & 3 — deep reasoning and strategy |
| `meta/llama-3.1-8b-instruct` | Phase 2 — fast structured JSON generation |

Both are accessed via the [NVIDIA Build API](https://build.nvidia.com) (`https://integrate.api.nvidia.com/v1`).

---

## Known Limitations

- Jobs are stored in memory; restarting the backend clears all active jobs.
- Fusion 360 API calls must execute on the main thread, which can limit parallelism inside the add-in.
- `simulation.py` currently copies the input file as output rather than modifying it — it only simulates the workflow, not the CAD operations.
- The NVIDIA API key is configured directly in `fastUpload.py` (no `.env` support yet).
