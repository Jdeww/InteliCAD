"""
API Client - HTTP communication between Fusion 360 add-in and backend
Uses only stdlib (no requests) since Fusion 360's Python env is limited.
"""

import urllib.request
import urllib.error
import json
import os


class APIClient:

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    def poll_jobs(self):
        """Poll for pending jobs - returns dict with awaiting_analysis and ready_for_execution"""
        try:
            return self._get("/poll-jobs/")
        except Exception as e:
            # Return empty dict on error so polling continues
            return {"awaiting_analysis": {}, "ready_for_execution": {}, "error": str(e)}

    # ------------------------------------------------------------------
    def submit_analysis(self, job_id, analysis_data):
        """Submit model analysis to backend"""
        try:
            return self._post_json(f"/jobs/{job_id}/analysis", analysis_data)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    def complete_job(self, job_id, output_file_path):
        """Upload the completed .f3d file back to the backend"""
        url = f"{self.base_url}/complete-job/{job_id}"

        try:
            with open(output_file_path, "rb") as f:
                file_data = f.read()

            boundary = "----InteliCADBoundary"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="output.f3d"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
            )
            
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
                
        except urllib.error.HTTPError as e:
            return {"status": "error", "message": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"status": "error", "message": f"Connection failed: {e.reason}"}
        except Exception as e:
            return {"status": "error", "message": f"Upload failed: {str(e)}"}

    # ------------------------------------------------------------------
    def retry_failed_operations(self, job_id, execution_results):
        """Request Phase 3 retry operations for failed operations"""
        try:
            return self._post_json(
                f"/retry-failed/{job_id}",
                {"execution_results": execution_results}
            )
        except Exception as e:
            return {"status": "error", "message": str(e), "retry_operations": []}

    # ------------------------------------------------------------------
    def _get(self, path):
        """Simple GET request"""
        try:
            url = f"{self.base_url}{path}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection failed: {e.reason}")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response")
        except Exception as e:
            raise Exception(f"GET {path} failed: {str(e)}")

    def _post_json(self, path, data):
        """Simple POST request with JSON body"""
        try:
            url = f"{self.base_url}{path}"
            body = json.dumps(data).encode()
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection failed: {e.reason}")
        except Exception as e:
            raise Exception(f"POST {path} failed: {str(e)}")