import os
import re
from pathlib import Path

from google import genai
from google.genai import types
from json_repair import repair_json

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

AGENTS_DIR = Path(__file__).parent.parent / "agents"
MODEL = "gemini-2.5-flash"

JSON_AGENTS = {"extractor", "classifier", "evaluator", "diagram-as-is", "diagram-improved"}

# Allowlist of agent names that callers may request.
ALLOWED_AGENTS = {
    "interviewer",
    "extractor",
    "classifier",
    "evaluator",
    "synthesizer",
    "diagram-as-is",
    "diagram-improved",
}

# Keywords that map a free-text business_type to a specialized interviewer slug.
# Checked in order; first match wins.
_INTERVIEWER_KEYWORDS: list[tuple[str, list[str]]] = [
    ("construction", ["construction", "contractor", "builder", "subcontractor", "general contractor", "remodel", "renovation", "masonry", "concrete", "framing", "drywall", "flooring"]),
    ("trades",       ["hvac", "plumbing", "plumber", "electrical", "electrician", "roofing", "roofer", "landscaping", "pest control", "janitorial", "cleaning service"]),
    ("restaurant",   ["restaurant", "food", "cafe", "catering", "bakery", "bar", "brewery", "kitchen", "diner", "bistro", "food truck"]),
    ("healthcare",   ["health", "medical", "clinic", "dental", "therapy", "therapist", "physician", "chiro", "physio", "mental health", "optometry", "veterinary", "vet"]),
    ("artisan",      ["etsy", "handmade", "artisan", "craft", "maker", "candle", "jewellery", "jewelry", "ceramics", "pottery", "woodwork", "textile", "printmaker", "resin", "stationery", "amazon handmade", "faire", "artfire", "shopify maker", "craft fair", "market stall"]),
    ("retail",       ["retail", "store", "shop", "ecommerce", "e-commerce", "boutique", "wholesale", "dispensary", "pharmacy"]),
]


def _resolve_interviewer_slug(business_type: str) -> str:
    """Return the specialized interviewer slug for a free-text business type, or '_base'."""
    lowered = business_type.lower()
    for slug, keywords in _INTERVIEWER_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return slug
    return "_base"


def load_agent(name: str) -> str:
    if name not in ALLOWED_AGENTS:
        raise ValueError(f"Unknown agent: {name}")
    path = AGENTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Agent prompt not found: {name}")
    return path.read_text()


def load_interviewer(business_type: str) -> str:
    """Load the best-matched specialized interviewer prompt for the given business type."""
    slug = _resolve_interviewer_slug(business_type)
    path = AGENTS_DIR / "interviewers" / f"{slug}.md"
    if not path.exists():
        path = AGENTS_DIR / "interviewers" / "_base.md"
    return path.read_text()


def to_gemini_messages(messages: list) -> list:
    """Convert {role: user/assistant, content: str} to Gemini format."""
    converted = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        converted.append({"role": role, "parts": [{"text": m["content"]}]})
    return converted


def repair_json_response(text: str) -> str:
    """Strip markdown fences and repair malformed JSON from model output."""
    text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    return repair_json(text, return_objects=False)


def stream_chat(messages: list, agent: str, business_type: str = ""):
    """Yield SSE text chunks for the interview agent."""
    if agent == "interviewer" and business_type:
        system_prompt = load_interviewer(business_type)
    else:
        system_prompt = load_agent(agent)
    for chunk in client.models.generate_content_stream(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2000,
        ),
        contents=to_gemini_messages(messages),
    ):
        if chunk.text:
            yield chunk.text


_ANALYSIS_AGENTS = {"extractor", "classifier", "evaluator", "synthesizer"}


def invoke_agent(agent: str, user_content: str, max_tokens: int = 4000, business_type: str = "") -> str:
    """Call a pipeline agent and return the text response."""
    system_prompt = load_agent(agent)
    if agent in _ANALYSIS_AGENTS and business_type:
        interviewer_prompt = load_interviewer(business_type)
        # Use only the first paragraph — the domain vocabulary / industry knowledge section
        domain_context = interviewer_prompt.split("\n\n")[0].strip()
        system_prompt = (
            f"Industry context for this analysis:\n{domain_context}\n\n"
            + system_prompt
        )
    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
        contents=user_content,
    )
    text = response.text
    if agent in JSON_AGENTS:
        text = repair_json_response(text)
    return text
