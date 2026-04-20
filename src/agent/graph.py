"""
Agentic job search for given resume -
1. Takes input as entire text of a resume,
2. Tools #1 - Parse profile text, Identifies key skills, experiences.
3. Tool #2 - searches for matching jobs from important job portals (e.g. Naukri, LinkedIn), whichever is possible,
4. Tool #3 - Parses the search results to have a list of jobs. Each job has a field 'summary' which contains - company name, position, location, and 'url' - which is the link to that particular job
5. returns the list of jobs.
"""

from typing import TypedDict, List, Dict, Any
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
import os

# ---------------------------
# Model
# ---------------------------
MODEL_NAME = os.getenv("MODEL_NAME")

model = init_chat_model(
    MODEL_NAME,
    temperature=0
)

# ---------------------------
# Structured Output Schema
# ---------------------------
class Profile(BaseModel):
    skills: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    experience_years: int = 0
    most_senior_role: str = "Software Engineer"


# ---------------------------
# State
# ---------------------------
class Job(TypedDict):
    summary: str
    url: str


class State(TypedDict):
    resume_text: str
    extracted_profile: Dict[str, Any]
    raw_jobs: List[Dict[str, Any]]
    jobs: List[Job]


# ---------------------------
# Tool 1: Extract profile
# ---------------------------
@tool
def extract_profile_tool(resume_text: str) -> Dict[str, Any]:
    """Extract skills, roles, experience, and most senior role from resume."""

    structured_model = model.with_structured_output(Profile)

    result = structured_model.invoke(
        f"""
        Analyze the resume and extract:
        - skills (technical + soft skills)
        - roles (all roles held)
        - total experience in years
        - most senior role held (highest level position)

        Resume:
        {resume_text}
        """
    )

    return result.dict()


# ---------------------------
# Tool 2: Search jobs
# ---------------------------
@tool
def search_jobs_tool(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search jobs based on extracted profile (mock implementation)."""

    if not isinstance(profile, dict):
        profile = {}

    role = profile.get("most_senior_role", "Software Engineer")
    skills = profile.get("skills", [])

    # 👉 Replace this with real APIs (SerpAPI, etc.)
    return [
        {
            "title": role,
            "company": "Microsoft",
            "location": "Hyderabad",
            "url": "https://jobs.microsoft.com/example"
        },
        {
            "title": f"{role} - Backend",
            "company": "Amazon",
            "location": "Bangalore",
            "url": "https://amazon.jobs/example"
        }
    ]


# ---------------------------
# Tool 3: Parse jobs
# ---------------------------
@tool
def parse_jobs_tool(raw_jobs: List[Dict[str, Any]]) -> List[Job]:
    """Convert raw job data into structured format."""

    parsed = []

    for job in raw_jobs:
        summary = f"{job.get('company')} - {job.get('title')} ({job.get('location')})"

        parsed.append({
            "summary": summary,
            "url": job.get("url", "")
        })

    return parsed


# ---------------------------
# Nodes
# ---------------------------
async def extract_profile_node(state: State):
    """Node: Extract structured profile"""

    result = extract_profile_tool.invoke({
        "resume_text": state["resume_text"]
    })

    return {
        "extracted_profile": result
    }


async def search_jobs_node(state: State):
    """Node: Search jobs using senior role"""

    profile = state.get("extracted_profile", {})

    if not isinstance(profile, dict) or not profile:
        profile = {
            "most_senior_role": "Software Engineer",
            "skills": []
        }

    jobs = search_jobs_tool.invoke({
        "profile": profile
    })

    return {"raw_jobs": jobs}


async def parse_jobs_node(state: State):
    """Node: Parse job results"""

    raw_jobs = state.get("raw_jobs", [])

    if not raw_jobs:
        return {"jobs": []}

    parsed = parse_jobs_tool.invoke({
        "raw_jobs": raw_jobs
    })

    return {"jobs": parsed}


# ---------------------------
# Graph
# ---------------------------
builder = StateGraph(State)

builder.add_node("extract_profile", extract_profile_node)
builder.add_node("search_jobs", search_jobs_node)
builder.add_node("parse_jobs", parse_jobs_node)

builder.add_edge(START, "extract_profile")
builder.add_edge("extract_profile", "search_jobs")
builder.add_edge("search_jobs", "parse_jobs")
builder.add_edge("parse_jobs", END)

# IMPORTANT: must be named 'graph'
graph = builder.compile()