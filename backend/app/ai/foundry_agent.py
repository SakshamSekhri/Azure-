import os
import json
import re
import time
from typing import Dict, Any, Type, Tuple, Optional, List
from pydantic import BaseModel, ValidationError
from openai import OpenAI

from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError, HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

from backend.app.config.settings import settings
from backend.app.core.logging import logger
from backend.app.schemas.foundry_assessment import AssessmentStartResponse
from backend.app.ai.prompts import (
    RESUME_ANALYSIS_SYSTEM_PROMPT,
    JOB_ANALYSIS_SYSTEM_PROMPT,
    LEARNING_PLAN_SYSTEM_PROMPT,
    ASSESSMENT_QUESTION_GENERATION_PROMPT,
    ASSESSMENT_RESULT_ANALYSIS_PROMPT,
    RAG_ANSWER_SYSTEM_PROMPT
)

# Portable Azure CLI discovery across Windows, Linux, Docker, and CI/CD
import shutil
from pathlib import Path

_custom_cli_path = os.environ.get("AZURE_CLI_PATH")
if _custom_cli_path and os.path.isdir(_custom_cli_path):
    if _custom_cli_path.lower() not in os.environ.get("PATH", "").lower():
        os.environ["PATH"] = f"{_custom_cli_path};{os.environ.get('PATH', '')}"
elif os.name == "nt" and not shutil.which("az"):
    _prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    _candidate_cli = Path(_prog_files) / "Microsoft SDKs" / "Azure" / "CLI2" / "wbin"
    if _candidate_cli.is_dir():
        os.environ["PATH"] = f"{_candidate_cli.as_posix()};{os.environ.get('PATH', '')}"

# Project-relative Azure configuration directory fallback if present
_project_azure_dir = Path(__file__).resolve().parent.parent.parent.parent / ".azure"
if _project_azure_dir.is_dir() and "AZURE_CONFIG_DIR" not in os.environ:
    os.environ["AZURE_CONFIG_DIR"] = str(_project_azure_dir)


class AzureFoundryAgentClient:
    """Authoritative Client for Microsoft AI Foundry Agent Service.
    Invokes the saved Prompt Agent:
      - Agent Name: PlacementPreparationAgent
      - Agent Version: 4
      - Model: gpt-5-mini
    Uses the Microsoft Foundry Responses API via agent-bound OpenAI client:
      project_client = AIProjectClient(endpoint=..., credential=DefaultAzureCredential(), allow_preview=True)
      openai_client = project_client.get_openai_client(agent_name=FOUNDRY_AGENT_NAME)
      response = openai_client.responses.create(input=...)
    Strict architectural invariants:
      - ZERO predefined or fallback questions anywhere in the system.
      - Azure AI Foundry is the sole generator for all assessment questions.
      - If Azure Foundry fails, explicit errors are raised; no fallback is used.
      - Status classification: LIVE_FOUNDRY, CACHED (for non-question ops).
      - Strict Pydantic response validation and schema verification.
    """

    def __init__(self):
        self.project_endpoint = (settings.FOUNDRY_PROJECT_ENDPOINT or "").strip()
        self.agent_name = (settings.FOUNDRY_AGENT_NAME or "PlacementPreparationAgent").strip()
        self.agent_version = str(settings.FOUNDRY_AGENT_VERSION or "4").strip()
        self.timeout = float(settings.AI_REQUEST_TIMEOUT_SECONDS)
        self._project_client: Optional[AIProjectClient] = None
        self._openai_client: Optional[OpenAI] = None
        self._agent_verified: bool = False

    def is_configured(self) -> bool:
        """Returns True only if Microsoft Foundry project endpoint is set."""
        return bool(self.project_endpoint)

    def get_credentials(self) -> DefaultAzureCredential:
        """Standard Microsoft credential resolution supporting 'az login'."""
        return DefaultAzureCredential()

    def get_project_client(self) -> AIProjectClient:
        """Lazy initialization of AIProjectClient with allow_preview=True."""
        if self._project_client is None:
            if not self.is_configured():
                raise RuntimeError(
                    "Azure AI Foundry Project Endpoint is not configured. "
                    "Please set FOUNDRY_PROJECT_ENDPOINT in .env."
                )
            credential = self.get_credentials()
            self._project_client = AIProjectClient(
                endpoint=self.project_endpoint,
                credential=credential,
                allow_preview=True
            )
        return self._project_client

    def get_openai_client(self) -> OpenAI:
        """Lazy initialization of agent-bound OpenAI client for PlacementPreparationAgent."""
        if self._openai_client is None:
            pc = self.get_project_client()
            self._openai_client = pc.get_openai_client(
                agent_name=self.agent_name,
                timeout=self.timeout,
                max_retries=0
            )
        return self._openai_client

    def verify_agent_version(self) -> Tuple[bool, str]:
        """Verify that PlacementPreparationAgent Version 4 exists in Foundry
        without invoking model inference (0 model tokens consumed).
        Uses the control-plane SDK method: project_client.agents.get_version.
        """
        try:
            pc = self.get_project_client()
            agent_details = pc.agents.get_version(
                agent_name=self.agent_name,
                agent_version=self.agent_version
            )
            status_val = getattr(agent_details, "status", "active")
            agent_id = getattr(agent_details, "id", self.agent_name)
            return True, f"Agent '{self.agent_name}' Version '{self.agent_version}' verified (id: {agent_id}, status: {status_val})."
        except Exception as e:
            return False, f"Agent verification failed for '{self.agent_name}' version '{self.agent_version}': {str(e)}"

    def _is_transient_error(self, exc: Exception) -> bool:
        """Determines whether an error is genuinely transient (rate limits, timeouts)."""
        if isinstance(exc, (ClientAuthenticationError,)):
            return False
        status_code = getattr(exc, "status_code", None)
        if status_code in (400, 401, 403, 404, 422):
            return False
        if status_code in (408, 429, 502, 503, 504):
            return True
        exc_str = f"{type(exc).__name__} {str(exc)}".lower()
        if "timeout" in exc_str or "connection reset" in exc_str or "connection refused" in exc_str:
            return True
        return False

    def _extract_text_from_response(self, response: Any) -> str:
        """Thoroughly extract output text from Azure AI Foundry Response object."""
        output_text = getattr(response, "output_text", "") or ""
        if output_text and output_text.strip():
            return output_text.strip()

        # Check response.output items (ResponseOutputMessage, etc.)
        if hasattr(response, "output") and response.output:
            for item in response.output:
                # If item has direct text
                if hasattr(item, "text") and item.text:
                    output_text += item.text + "\n"
                # If item is ResponseOutputMessage with content list
                elif hasattr(item, "content") and item.content:
                    for c in item.content:
                        if hasattr(c, "text") and c.text:
                            output_text += c.text + "\n"
                # If item has message or string
                elif isinstance(item, str):
                    output_text += item + "\n"

        if output_text.strip():
            return output_text.strip()

        raise ValueError("Azure AI Foundry agent returned an empty response.")

    def _extract_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Safely parse JSON from raw agent response text."""
        cleaned = raw_text.strip()

        # 1. Direct JSON parse
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # 2. Markdown code fence ```json ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass

        # 3. Outermost braces { ... } or brackets [ ... ]
        start_brace = cleaned.find("{")
        end_brace = cleaned.rfind("}")
        start_bracket = cleaned.find("[")
        end_bracket = cleaned.rfind("]")

        if start_bracket != -1 and end_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
            try:
                return json.loads(cleaned[start_bracket:end_bracket + 1])
            except Exception:
                pass

        if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
            try:
                return json.loads(cleaned[start_brace:end_brace + 1])
            except Exception:
                pass

        raise ValueError(
            f"Could not extract a valid JSON object from the Foundry agent response. Response was: {raw_text[:200]}..."
        )

    def _normalize_parsed_data(self, operation_type: str, parsed_data: Any, payload: Dict[str, Any]) -> Any:
        """Normalize slight schema variations in LLM response to match Pydantic expectations."""
        if operation_type == "LEARNING_PLAN":
            if isinstance(parsed_data, list):
                parsed_data = {
                    "target_role": payload.get("target_role", "Target Role"),
                    "overview": f"7-day personalized curriculum for {payload.get('target_role', 'Target Role')}",
                    "days": parsed_data
                }
            elif isinstance(parsed_data, dict):
                if "target_role" not in parsed_data:
                    parsed_data["target_role"] = payload.get("target_role", "Target Role")
                if "overview" not in parsed_data:
                    parsed_data["overview"] = f"Personalized learning plan for {parsed_data.get('target_role')}"
                if "days" not in parsed_data:
                    if "plan" in parsed_data and isinstance(parsed_data["plan"], list):
                        parsed_data["days"] = parsed_data.pop("plan")
                    elif "activities" in parsed_data and isinstance(parsed_data["activities"], list):
                        parsed_data["days"] = parsed_data.pop("activities")
        elif operation_type == "ASSESSMENT_RESULT_ANALYSIS" and isinstance(parsed_data, dict):
            for field in ["improvement_plan", "strengths", "weaknesses", "skill_gaps", "prioritized_study_areas"]:
                if field in parsed_data and isinstance(parsed_data[field], list):
                    normalized_list = []
                    for item in parsed_data[field]:
                        if isinstance(item, dict):
                            parts = [f"{k}: {v}" for k, v in item.items() if v]
                            normalized_list.append(" - ".join(parts) if parts else str(item))
                        else:
                            normalized_list.append(str(item))
                    parsed_data[field] = normalized_list
        elif operation_type == "ASSESSMENT_QUESTION_GENERATION" and isinstance(parsed_data, dict):
            questions = parsed_data.get("questions", [])
            for q in questions:
                opts = q.get("options", [])
                corr = q.get("correct_answer")
                if corr not in opts and opts:
                    matched = next((o for o in opts if o.strip().lower() == str(corr).strip().lower()), None)
                    if matched:
                        q["correct_answer"] = matched
                    else:
                        opts.append(corr)
        return parsed_data

    def _build_task_prompt(
        self,
        operation_type: str,
        payload: Dict[str, Any],
        response_model: Type[BaseModel]
    ) -> str:
        """Constructs a context-rich prompt tailored for PlacementPreparationAgent."""
        if operation_type == "ASSESSMENT_QUESTION_GENERATION":
            role = payload.get("role", "Software Engineer")
            jd = payload.get("job_description", "")
            resume = payload.get("resume", "")
            num_q = int(payload.get("num_questions", 5))
            difficulty = payload.get("difficulty", "Intermediate")
            cand_skills = payload.get("candidate_skills", [])
            cand_projects = payload.get("candidate_projects", [])
            cand_experience = payload.get("candidate_experience", [])
            cand_education = payload.get("candidate_education", [])
            cand_certifications = payload.get("candidate_certifications", [])
            gaps = payload.get("identified_gaps", [])
            prev_perf = payload.get("previous_performance", [])
            prev_score = payload.get("previous_score")
            excluded_questions = payload.get("excluded_questions", [])
            excluded_concepts = payload.get("excluded_concepts", [])

            excluded_section = ""
            if excluded_questions or excluded_concepts:
                excluded_section = "\n\nDUPLICATE PREVENTION RESTRICTIONS:\n"
                if excluded_questions:
                    excluded_section += "DO NOT repeat or generate questions similar to these previously asked questions:\n" + "\n".join(f"- {q}" for q in excluded_questions[:15]) + "\n"
                if excluded_concepts:
                    excluded_section += "DO NOT repeat or test these previously evaluated concepts:\n" + "\n".join(f"- {c}" for c in excluded_concepts[:20]) + "\n"

            return (
                f"{ASSESSMENT_QUESTION_GENERATION_PROMPT}\n\n"
                f"--- GENERATION CONTEXT ---\n"
                f"Target Role: {role}\n"
                f"Requested Question Count: {num_q}\n"
                f"Target Difficulty: {difficulty}\n\n"
                f"Job Description Requirements:\n{jd}\n\n"
                f"Candidate Verified Resume / Background:\n{resume}\n\n"
                f"Candidate Extracted Details:\n"
                f"- Skills: {json.dumps(cand_skills)}\n"
                f"- Projects: {json.dumps(cand_projects)}\n"
                f"- Experience: {json.dumps(cand_experience)}\n"
                f"- Education: {json.dumps(cand_education)}\n"
                f"- Certifications: {json.dumps(cand_certifications)}\n"
                f"- Identified Skill Gaps vs JD: {json.dumps(gaps)}\n"
                f"- Previous Assessment History (Average Score: {prev_score}%): {json.dumps(prev_perf)}\n"
                f"{excluded_section}\n\n"
                f"MANDATORY INSTRUCTIONS:\n"
                f"1. Generate EXACTLY {num_q} dynamically personalized multiple choice questions (MCQs).\n"
                f"2. Every question MUST have 4 options.\n"
                f"3. 'correct_answer' MUST EXACTLY MATCH one of the strings in 'options'.\n"
                f"4. Questions MUST deeply evaluate the candidate's actual projects, claimed skills, target role, and JD skill gaps.\n"
                f"5. Each question must include 'skill' (clean, standard skill name), 'topic' (domain sub-area), and 'concept' (granular principle/pattern/mechanism tested).\n"
                f"6. NO generic trivia. Include 'why_the_question_is_relevant' for every question explaining the exact link.\n"
                f"7. Zero duplicates: Every question in this set MUST test a distinct concept. Never test the same concept twice in one assessment.\n"
                f"8. Output ONLY a valid JSON object matching the schema with keys: 'title', 'role', 'total_questions', 'overview', 'questions'."
            )

        if operation_type == "ASSESSMENT_RESULT_ANALYSIS":
            role = payload.get("role", "Software Engineer")
            score = payload.get("score_percentage", 0)
            return (
                f"{ASSESSMENT_RESULT_ANALYSIS_PROMPT}\n\n"
                f"--- PERFORMANCE CONTEXT ---\n"
                f"Target Role: {role}\n"
                f"Objective Score: {score}%\n"
                f"Candidate Assessment Performance Data:\n"
                f"{json.dumps(payload, default=str)}\n\n"
                f"MANDATORY INSTRUCTIONS:\n"
                f"1. Analyze strengths, weaknesses, critical skill gaps, and granular topics to improve based on the candidate's actual answers.\n"
                f"2. Prioritize key areas by educational impact (JD importance + gap + study effort).\n"
                f"3. Generate a concrete personalized improvement plan with recommended sequence.\n"
                f"4. Provide realistic reassessment guidance.\n"
                f"5. Output ONLY a valid JSON object matching the schema."
            )

        if operation_type == "RESUME_ANALYSIS":
            return (
                f"{RESUME_ANALYSIS_SYSTEM_PROMPT}\n\n"
                f"--- CANDIDATE RESUME INPUT ---\n"
                f"{payload.get('raw_text', '')}\n\n"
                f"Extract structured information strictly adhering to the schema. Output ONLY valid JSON."
            )

        if operation_type == "JOB_ANALYSIS":
            return (
                f"{JOB_ANALYSIS_SYSTEM_PROMPT}\n\n"
                f"--- JOB DESCRIPTION INPUT ---\n"
                f"Title: {payload.get('title', '')}\n"
                f"Company: {payload.get('company', '')}\n"
                f"Text:\n{payload.get('raw_text', '')}\n\n"
                f"Extract structured technical and domain requirements strictly adhering to the schema. Output ONLY valid JSON."
            )

        if operation_type == "LEARNING_PLAN":
            return (
                f"{LEARNING_PLAN_SYSTEM_PROMPT}\n\n"
                f"--- LEARNING PLAN INPUT ---\n"
                f"Target Role: {payload.get('target_role', '')}\n"
                f"Weak Skills / Gaps: {json.dumps(payload.get('weak_skills', []))}\n"
                f"Strong Skills: {json.dumps(payload.get('strong_skills', []))}\n\n"
                f"Generate a progressive 7-day curriculum. Output ONLY valid JSON."
            )

        if operation_type == "RAG_ANSWER":
            target_role = payload.get("target_role") or "Placement Preparation Candidate"
            return (
                f"{RAG_ANSWER_SYSTEM_PROMPT}\n\n"
                f"Candidate Active Target Role: {target_role}\n"
                f"Topic: {payload.get('topic', 'General')}\n"
                f"Question: {payload.get('question', '')}\n\n"
                f"Retrieved Knowledge Context:\n{json.dumps(payload.get('context_docs', []))}\n\n"
                f"MANDATORY EXECUTION INSTRUCTIONS:\n"
                f"1. First verify if the question is strictly within professional career placement preparation for '{target_role}'.\n"
                f"2. If the inquiry is elementary science (e.g. 'what is water', 'why is sky blue'), everyday object definitions, general trivia, casual chitchat, or unrelated to '{target_role}', you MUST REJECT under TIER 3 with confidence: 'None', grounded: false, citations: [], and the polite refusal in 'answer'.\n"
                f"3. Only if it is genuinely relevant to '{target_role}' competencies, frameworks, or interview preparation, provide an interview-ready response under Tier 1 (if retrieved sources match) or Tier 2 (role synthesis).\n"
                f"4. Output ONLY valid JSON adhering to the schema."
            )

        # General JSON operation
        schema_props = response_model.model_json_schema().get("properties", {})
        required_keys = list(schema_props.keys())
        return (
            f"Operation: {operation_type}\n"
            f"Required Output: Strict JSON object containing keys: {json.dumps(required_keys)}.\n"
            f"No conversational text outside the JSON object.\n\n"
            f"Data:\n{json.dumps(payload, default=str)}"
        )

    def _call_foundry_with_retry(self, task_prompt: str) -> Any:
        """Execute call to saved Foundry Agent via Responses API with at most 1 controlled retry for transient errors."""
        max_attempts = 2
        last_exc = None

        for attempt in range(1, max_attempts + 1):
            try:
                openai_client = self.get_openai_client()
                response = openai_client.responses.create(
                    input=task_prompt,
                    timeout=self.timeout
                )
                return response
            except Exception as e:
                last_exc = e
                if attempt < max_attempts and self._is_transient_error(e):
                    logger.warning(
                        f"Transient error calling Azure AI Foundry ({type(e).__name__}: {e}). "
                        f"Retrying (attempt {attempt + 1}/{max_attempts})..."
                    )
                    time.sleep(1.5)
                    continue
                break

        raise last_exc

    def execute_operation(
        self,
        operation_type: str,
        payload: Dict[str, Any],
        response_model: Type[BaseModel]
    ) -> Tuple[BaseModel, int, str]:
        """Execute an AI operation against Microsoft Foundry PlacementPreparationAgent v4.
        Returns: (validated_pydantic_model, tokens_used, status_flag="LIVE_FOUNDRY")
        Raises descriptive exceptions if Azure AI Foundry is unconfigured or fails.
        """
        if not self.is_configured():
            raise RuntimeError(
                "Microsoft Azure AI Foundry is not configured. "
                "FOUNDRY_PROJECT_ENDPOINT is missing in .env."
            )

        # Verify Agent Version 4 before first live request
        if not self._agent_verified:
            verified, verify_msg = self.verify_agent_version()
            if not verified:
                logger.error(f"[AGENT_VERIFICATION_FAILED] {verify_msg}")
                raise RuntimeError(f"Azure AI Foundry Agent verification failed: {verify_msg}")
            self._agent_verified = True
            logger.info(f"[AGENT_VERIFIED] {verify_msg}")

        task_prompt = self._build_task_prompt(operation_type, payload, response_model)

        logger.info(
            f"Calling Azure AI Foundry agent '{self.agent_name}' (v{self.agent_version}) "
            f"for operation '{operation_type}'..."
        )

        try:
            response = self._call_foundry_with_retry(task_prompt)
            output_text = self._extract_text_from_response(response)

            tokens_used = 0
            if hasattr(response, "usage") and response.usage:
                tokens_used = getattr(response.usage, "total_tokens", 0) or 0

            # Parse and validate JSON against Pydantic schema
            try:
                parsed_dict = self._extract_and_parse_json(output_text)
                parsed_dict = self._normalize_parsed_data(operation_type, parsed_dict, payload)
                validated_model = response_model.model_validate(parsed_dict)

            except (ValueError, ValidationError) as parse_err:
                logger.warning(
                    f"First attempt to parse/validate Foundry response failed: {parse_err}. "
                    f"Requesting corrective regeneration from Foundry..."
                )
                correction_prompt = (
                    f"{task_prompt}\n\n"
                    f"IMPORTANT CORRECTION: Your previous response was invalid: {str(parse_err)[:300]}.\n"
                    f"Output ONLY valid JSON strictly matching the requested schema with no extra text."
                )
                retry_response = self._call_foundry_with_retry(correction_prompt)
                retry_output = self._extract_text_from_response(retry_response)
                retry_parsed = self._extract_and_parse_json(retry_output)
                retry_parsed = self._normalize_parsed_data(operation_type, retry_parsed, payload)
                validated_model = response_model.model_validate(retry_parsed)
                if hasattr(retry_response, "usage") and retry_response.usage:
                    tokens_used += getattr(retry_response.usage, "total_tokens", 0) or 0

            logger.info(
                f"Azure AI Foundry agent '{self.agent_name}' successfully executed '{operation_type}'. "
                f"Tokens consumed: {tokens_used}."
            )
            return validated_model, tokens_used, "LIVE_FOUNDRY"

        except Exception as e:
            logger.error(f"Azure AI Foundry call failed for '{operation_type}': {type(e).__name__}: {str(e)}")
            raise e


foundry_client = AzureFoundryAgentClient()
