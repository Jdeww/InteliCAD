"""
API Client for communicating with the InteliCAD backend server
"""

import urllib.request
import urllib.error
import json
import os


class APIClient:
    """
    Handles all HTTP communication with the backend server
    """
    
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    def poll_jobs(self):
        """
        Poll the backend for available jobs
        Returns: dict with 'awaiting_analysis' and 'ready_for_execution'
        """
        try:
            url = f"{self.base_url}/poll-jobs/"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                return json.loads(data.decode('utf-8'))
                
        except urllib.error.URLError as e:
            print(f"Network error polling jobs: {e}")
            return {'awaiting_analysis': {}, 'ready_for_execution': {}}
        except Exception as e:
            print(f"Error polling jobs: {e}")
            return {'awaiting_analysis': {}, 'ready_for_execution': {}}
    
    def submit_analysis(self, job_id, analysis_data):
        """
        Submit model analysis data to the backend
        """
        try:
            url = f"{self.base_url}/jobs/{job_id}/analysis"
            
            data = json.dumps(analysis_data).encode('utf-8')
            req = urllib.request.Request(
                url, 
                data=data,
                method='POST',
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = response.read()
                return json.loads(result.decode('utf-8'))
                
        except Exception as e:
            print(f"Error submitting analysis: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def download_file(self, file_path):
        """
        Download a file from the backend
        Returns: local path to downloaded file
        """
        try:
            # For local files, just return the path
            # In production, you'd use the file server URL
            if os.path.exists(file_path):
                return file_path
            
            # If it's a URL, download it
            temp_dir = os.path.join(os.environ['TEMP'], 'intelicad')
            os.makedirs(temp_dir, exist_ok=True)
            
            local_path = os.path.join(temp_dir, os.path.basename(file_path))
            
            # Note: This assumes file_path is accessible
            # In production, you'd have a proper download endpoint
            import shutil
            shutil.copy2(file_path, local_path)
            
            return local_path
            
        except Exception as e:
            print(f"Error downloading file: {e}")
            return None
    
    def complete_job(self, job_id, output_file_path):
        """
        Upload completed file back to the backend
        """
        try:
            url = f"{self.base_url}/complete-job/{job_id}"
            
            # Read the file
            with open(output_file_path, 'rb') as f:
                file_data = f.read()
            
            # Create multipart form data
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            
            body = (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="file"; filename="output.f3d"\r\n'
                f'Content-Type: application/octet-stream\r\n\r\n'
            ).encode('utf-8')
            body += file_data
            body += f'\r\n--{boundary}--\r\n'.encode('utf-8')
            
            req = urllib.request.Request(
                url,
                data=body,
                method='POST',
                headers={
                    'Content-Type': f'multipart/form-data; boundary={boundary}'
                }
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                result = response.read()
                return json.loads(result.decode('utf-8'))
                
        except Exception as e:
            print(f"Error completing job: {e}")
            return {'status': 'error', 'message': str(e)}
