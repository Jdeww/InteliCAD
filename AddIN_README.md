# InteliCAD - Fusion 360 Add-In

AI-Powered CAD modification add-in for Autodesk Fusion 360. Connects to your InteliCAD backend server to execute intelligent design modifications based on natural language commands.

## Features

- 🤖 **AI-Driven Operations**: Nemotron AI interprets complex design intent
- 📊 **Automated Analysis**: Extracts model properties (mass, volume, features)
- ⚙️ **Smart Execution**: Executes CAD operations with validation
- 🔄 **Background Polling**: Continuously checks for new jobs
- 📈 **Real-time Feedback**: Console output shows operation progress

## Installation

### Step 1: Locate Fusion 360 Add-ins Folder

**Windows:**
```
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
```

**Mac:**
```
~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/
```

### Step 2: Install the Add-In

1. Copy the entire `InteliCAD` folder to the Add-ins directory
2. Your folder structure should look like:
   ```
   AddIns/
   └── InteliCAD/
       ├── InteliCAD.py
       ├── InteliCAD.manifest
       ├── api_client.py
       ├── model_analyzer.py
       ├── operation_executor.py
       └── ui_manager.py
   ```

### Step 3: Enable the Add-In in Fusion 360

1. Open Fusion 360
2. Go to **Utilities** → **Add-Ins** → **Scripts and Add-Ins**
3. Click the **Add-Ins** tab
4. Find **InteliCAD** in the list
5. Click **Run** to start it

**For automatic startup:**
- Check the "Run on Startup" checkbox next to InteliCAD

## Configuration

### Backend URL

By default, the add-in connects to `http://127.0.0.1:8000`

To change this, edit `InteliCAD.py`:
```python
BACKEND_URL = "http://your-server-url:8000"
```

### Poll Interval

Jobs are polled every 10 seconds by default. To change:
```python
POLL_INTERVAL = 10  # seconds
```

## Usage

### 1. Start Your Backend Server

```bash
uvicorn fastUpload:app --reload
```

### 2. Submit a Job via Web Interface

Upload a .f3d file with a command like:
- "Make this lighter without compromising structural integrity"
- "Reduce material usage by 40% while maintaining strength for a 20kg load"

### 3. Watch the Add-In Work

The add-in will:
1. **Poll** the backend for new jobs
2. **Download** the .f3d file
3. **Analyze** the model (extract mass, volume, features)
4. **Submit** analysis data back to the backend
5. **Wait** for Nemotron to refine operations
6. **Execute** the AI-generated operations
7. **Upload** the modified file back

### 4. Download Your Result

Check the job status in your web interface and download the modified file!

## Monitoring

### Text Commands Window

Open Fusion's **Text Commands** window to see detailed logs:
1. Press `Ctrl + Shift + C` (Windows) or `Cmd + Shift + C` (Mac)
2. You'll see output like:

```
================================================================================
📊 ANALYZING JOB: abc-123-def
Command: 'Make this lighter without compromising structural integrity'
================================================================================

✓ Analysis complete:
  Mass: 150.5g
  Volume: 125.3cm³
  Bodies: 1

✓ Analysis submitted to backend
  Status: success

================================================================================
⚙️  EXECUTING JOB: abc-123-def
Command: 'Make this lighter without compromising structural integrity'
================================================================================

📋 Executing 3 operations...

  Operation 1/3: shell_body
  ✓ Success

  Operation 2/3: add_ribs
  ✓ Success

  Operation 3/3: fillet_edges
  ✓ Success

✓ Job abc-123-def completed and uploaded
```

## Implemented Operations

### Fully Implemented ✅
- **scale**: Uniform and non-uniform scaling
- **shell_body**: Hollow out solid bodies
- **fillet / fillet_edges**: Round sharp edges
- **mirror**: Mirror geometry across planes
- **rotate**: Rotate around axes
- **move**: Translate geometry

### Partially Implemented ⚠️
- **add_ribs**: Basic implementation (needs refinement)
- **pattern**: Placeholder (linear/circular patterns)
- **extrude**: Placeholder

### Placeholders (Future) 🚧
- **lattice_infill**: Requires mesh generation
- **topology_optimization**: Requires generative design API
- **variable_wall_thickness**: Complex operation
- **add_gussets**: Reinforcement features
- **draft_angles**: Manufacturing optimization
- **add_ventilation**: Hole patterns

## Troubleshooting

### Add-In Not Appearing

1. Check folder is in correct location
2. Restart Fusion 360
3. Check for Python errors in Text Commands window

### Connection Errors

```
Network error polling jobs
```
**Solution**: Make sure your backend server is running on `http://127.0.0.1:8000`

### Operations Failing

Check the console output for specific errors. Common issues:
- Model has no solid bodies (can't shell)
- No edges found for filleting
- Complex geometry causing operation failures

## Development

### Adding New Operations

1. Add handler method to `operation_executor.py`:
   ```python
   def execute_my_operation(self, params):
       # Your implementation
       return "Operation result message"
   ```

2. Register it in the `handlers` dict:
   ```python
   handlers = {
       'my_operation': self.execute_my_operation,
       ...
   }
   ```

### Debugging

Enable verbose logging by modifying the exception handlers to print full tracebacks.

## Architecture

```
┌─────────────────┐
│  Web Interface  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  FastAPI Backend│◄────►│   Nemotron   │
└────────┬────────┘      │  (AI Model)  │
         │               └──────────────┘
         ▼
┌─────────────────┐
│ Fusion 360 Add-In│
│                 │
│ ┌─────────────┐ │
│ │API Client   │ │
│ ├─────────────┤ │
│ │Model Analyzer│ │
│ ├─────────────┤ │
│ │Op Executor  │ │
│ └─────────────┘ │
└─────────────────┘
```

## Workflow

1. **User** → Uploads .f3d + text command
2. **Backend** → Nemotron analyzes intent
3. **Add-In** → Downloads file, analyzes model
4. **Backend** → Nemotron refines operations with model data
5. **Add-In** → Executes operations
6. **Backend** → Serves modified file to user

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Check the console output in Fusion 360
- Review the backend server logs
- Ensure all dependencies are installed

## Future Enhancements

- [ ] FEA integration for stress analysis
- [ ] Real lattice structure generation
- [ ] Topology optimization via generative design API
- [ ] Progress notifications in UI
- [ ] Operation preview before execution
- [ ] Undo/rollback functionality
- [ ] Batch processing of multiple files
