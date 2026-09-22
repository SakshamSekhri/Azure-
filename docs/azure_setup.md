# Microsoft Foundry Agent & Azure AI Search Setup Guide

This document provides setup instructions for configuring **Microsoft Foundry Agent Service** and **Azure AI Search** for the Placement Preparation Agent platform.

---

## 1. Prerequisites
- An active Microsoft Azure subscription with access to Azure AI Foundry.
- Azure CLI installed (`az login` for local developer authentication).
- Python 3.12+.

---

## 2. Microsoft Foundry Prompt Agent Architecture

The application is integrated with your saved **Microsoft Foundry Prompt Agent**:
- **Agent Name**: `PlacementPreparationAgent`
- **Agent Version**: `4`
- **Model Deployment**: `gpt-5-mini` (Global Standard)
- **Features**: Web Search enabled
- **Inference API**: Microsoft Foundry Responses API via agent-bound client (`get_openai_client(agent_name="PlacementPreparationAgent")` -> `openai_client.responses.create(input=...)`)
- **Control Plane Verification**: `project_client.agents.get_version(agent_name="PlacementPreparationAgent", agent_version="4")` (0 inference tokens consumed)

---

## 3. Configuring Environment Variables

Configure your `.env` file in the project root with the following keys:

```env
# Microsoft Foundry Agent Configuration
FOUNDRY_PROJECT_ENDPOINT="https://sakshamsekhri51-0435-resource.services.ai.azure.com/api/projects/sakshamsekhri51-0435"
FOUNDRY_AGENT_NAME="PlacementPreparationAgent"
FOUNDRY_AGENT_VERSION="4"

# AI Gateway Credit Control Settings
AI_CACHE_ENABLED=true

# Azure AI Search (Optional Knowledge Retrieval Layer)
AZURE_AI_SEARCH_ENDPOINT=""
AZURE_AI_SEARCH_KEY=""
AZURE_AI_SEARCH_INDEX="placement-prep-knowledge"

# GitHub REST API (Optional for higher rate limits)
GITHUB_TOKEN=""
```

---

## 4. Local Authentication via Azure CLI

To authenticate locally for live Foundry inference without embedding secret keys in code:
```bash
az login
```
The SDK uses `DefaultAzureCredential` from `azure-identity`, which automatically recognizes your active Azure CLI credentials.

---

## 5. Live Foundry Operation & Credit Conservation
 
1. **Credit-Conscious Caching**:
   - The centralized `AIGateway` computes a SHA-256 hash across the operation type, agent version, and request payload.
   - For non-assessment operations (resume skill extraction, JD competency extraction), cache hits return in sub-10ms and consume **0 model tokens**.
   - Assessment question generation always runs live via Azure AI Foundry to ensure fresh, dynamic, and unique questions tailored to candidate history.

2. **Zero Predefined Questions & Strict Error Transparency**:
   - Zero hardcoded questions, mock question generators, or fallback question providers exist in the platform.
   - If Azure AI Foundry is unreachable or unauthenticated, an explicit HTTP error is raised immediately. No fake or fallback questions are ever returned.
