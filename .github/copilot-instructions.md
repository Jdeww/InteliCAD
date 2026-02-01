# Copilot Instructions for GTC 2026 Golden Ticket Project

## Project Architecture
- **Language**: Python 3.13.9
- **Environment**: Virtual environment located in `venv/` directory
- **Structure**: Source code should be organized in the workspace root or subdirectories as needed

## Development Setup
- Activate virtual environment: `venv\Scripts\activate` (Windows PowerShell)
- Install dependencies: `pip install package_name` (after activation)
- Run Python scripts: `python script.py`

## Key Patterns
- Use standard Python naming conventions (PEP 8)
- Place configuration files in root or `config/` directory
- Data files and assets in `data/` or `assets/` subdirectories

## Workflows
- **Testing**: Use `python -m pytest` for unit tests (install pytest if needed)
- **Linting**: Use `python -m flake8` or similar for code quality
- **Version Control**: Commit to git, ignore venv files via `.gitignore`

## Dependencies
- Core Python 3.13
- Additional packages installed via pip in the virtual environment

## Notes
- This project appears to be in early stages; update these instructions as the codebase grows
- Focus on modular, readable code with clear docstrings