import requests
from typing import Optional, Dict, Any, List
import streamlit as st


class APIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/api/v1"):
        self.base_url = base_url.rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        token = st.session_state.get("auth_token")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def register(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/register"
        res = requests.post(url, json={"email": email, "password": password})
        if res.status_code != 201:
            raise Exception(res.json().get("detail", "Registration failed."))
        return res.json()

    def login(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/login-json"
        res = requests.post(url, json={"email": email, "password": password})
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Login failed."))
        data = res.json()
        st.session_state["auth_token"] = data.get("access_token")
        st.session_state["user_info"] = data.get("user")
        return data

    def get_profile(self) -> Dict[str, Any]:
        url = f"{self.base_url}/profile"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def update_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/profile"
        res = requests.put(url, headers=self._get_headers(), json=payload)
        res.raise_for_status()
        return res.json()

    def upload_resume(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        url = f"{self.base_url}/resume/upload"
        files = {"file": (filename, file_bytes)}
        res = requests.post(url, headers=self._get_headers(), files=files)
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Resume upload failed."))
        return res.json()

    def analyze_resume(self, resume_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        url = f"{self.base_url}/resume/analyze"
        res = requests.post(url, headers=self._get_headers(), json={"resume_id": resume_id, "force_refresh": force_refresh})
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Resume analysis failed."))
        return res.json()

    def get_latest_resume(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/resume/latest"
        res = requests.get(url, headers=self._get_headers())
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return res.json()

    def create_job(self, title: str, raw_text: str, company: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/jobs"
        res = requests.post(url, headers=self._get_headers(), json={"title": title, "raw_text": raw_text, "company": company})
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Job creation failed."))
        return res.json()

    def analyze_job(self, job_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        url = f"{self.base_url}/jobs/analyze"
        res = requests.post(url, headers=self._get_headers(), json={"job_id": job_id, "force_refresh": force_refresh})
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Job analysis failed."))
        return res.json()

    def get_latest_job(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/jobs/latest"
        res = requests.get(url, headers=self._get_headers())
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return res.json()

    def get_dashboard_summary(self) -> Dict[str, Any]:
        url = f"{self.base_url}/dashboard/summary"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_skill_matrix(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/skills/matrix"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_skill_gaps(self) -> Dict[str, Any]:
        url = f"{self.base_url}/skills/gaps"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_candidate_vs_jd(self) -> Dict[str, Any]:
        url = f"{self.base_url}/skills/candidate-vs-jd"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_recommended_action(self) -> Dict[str, Any]:
        url = f"{self.base_url}/skills/recommended-action"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def connect_github(self, username: str) -> Dict[str, Any]:
        url = f"{self.base_url}/github/connect"
        res = requests.post(url, headers=self._get_headers(), json={"username": username})
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "GitHub analysis failed."))
        return res.json()

    def list_assessments(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/assessments"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_assessment(self, assessment_id: int) -> Dict[str, Any]:
        url = f"{self.base_url}/assessments/{assessment_id}"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def submit_assessment(self, assessment_id: int, answers: Dict[str, str]) -> Dict[str, Any]:
        url = f"{self.base_url}/assessments/{assessment_id}/submit"
        res = requests.post(url, headers=self._get_headers(), json={"assessment_id": assessment_id, "answers": answers})
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Assessment submission failed."))
        return res.json()

    def get_assessment_result(self, assessment_id: int) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/assessments/{assessment_id}/result"
        res = requests.get(url, headers=self._get_headers())
        if res.status_code == 200:
            return res.json()
        return None

    def get_assessment_history(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/assessments/history"
        res = requests.get(url, headers=self._get_headers())
        if res.status_code == 200:
            return res.json()
        return []

    def get_current_plan(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/learning/plan"
        res = requests.get(url, headers=self._get_headers())
        if res.status_code == 200:
            return res.json()
        return None

    def generate_plan(self, target_role: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        url = f"{self.base_url}/learning/plan/generate"
        res = requests.post(url, headers=self._get_headers(), json={"target_role": target_role, "force_refresh": force_refresh})
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Plan generation failed."))
        return res.json()

    def toggle_activity(self, activity_id: int, completed: bool) -> Dict[str, Any]:
        url = f"{self.base_url}/learning/activity/toggle"
        res = requests.post(url, headers=self._get_headers(), json={"activity_id": activity_id, "completed": completed})
        res.raise_for_status()
        return res.json()

    def ask_rag_question(self, question: str, topic: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/learning/ask"
        res = requests.post(url, headers=self._get_headers(), json={"question": question, "topic": topic})
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Failed to retrieve educational answer."))
        return res.json()

    def generate_personalized_assessment(
        self,
        role: str,
        job_description: Optional[str] = None,
        resume: Optional[str] = None,
        num_questions: int = 5
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/assessments/personalized/generate"
        payload = {
            "role": role,
            "job_description": job_description,
            "resume": resume,
            "num_questions": num_questions
        }
        res = requests.post(url, headers=self._get_headers(), json=payload)
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Failed to generate personalized assessment."))
        return res.json()


    def list_evidence(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/evidence"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_ai_usage(self) -> Dict[str, Any]:
        url = f"{self.base_url}/ai/usage"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_ai_logs(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/ai/logs"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()


api = APIClient()
