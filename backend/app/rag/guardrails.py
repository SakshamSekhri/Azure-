"""Technical & Role-Aware Domain Guardrails for RAG Knowledge Assistant.
Ensures inquiries remain strictly bounded to the candidate's chosen target role
(whether technical like Software Engineering or non-technical like Marketing, Product, etc.)
and career placement preparation.
Rejects out-of-bound inquiries (unrelated physics/thermodynamics, cooking, sports,
entertainment, etc.) with Tier 3 Domain Guardrail.
"""
import re
from typing import Tuple, Optional


# 1. Universal Off-Topic Patterns (Off-bounds for ANY professional career preparation)
UNIVERSAL_OFF_TOPIC_PATTERNS = [
    # Everyday Object & Elementary Definitions (e.g. "whats water", "what is a dog", "define chair")
    (
        r"^(what('?s|\s+is)|\bdefine|\bexplain|\btell\s+me\s+about)\s+(a\s+|an\s+|the\s+)?(water|air|food|milk|coffee|tea|chair|table|apple|banana|car|dog|cat|bird|tree|grass|sun|moon|sky|cloud|rain|snow|fire|dirt|stone|rock|house|shoe|shirt|bed|clock|door|window)[\?\.\!\s]*$",
        "Everyday Object / Elementary Concept Definition"
    ),
    # Elementary Chemistry & Water / Nature Facts
    (
        r"\b(((properties|formula|density|freezing\s+point|boiling\s+point|surface\s+tension|chemical\s+formula|states|molecular\s+weight)\s+of\s+water)|(why\s+is|is)\s+water\s+wet|what\s+is\s+water\s+made\s+of|h2o\s+molecule|composition\s+of\s+water)\b",
        "Elementary Chemistry / Water Properties"
    ),
    (
        r"\b(why\s+is\s+(the\s+sky\s+blue|grass\s+green|snow\s+white|fire\s+hot|ocean\s+salty)|how\s+do\s+(birds\s+fly|fish\s+breathe|plants\s+grow))\b",
        "Elementary Nature Trivia"
    ),
    # Culinary & Food Recipes
    (
        r"\b(recipe|how\s+to\s+(bake|cook|fry|grill|roast|steam|make|prepare)|ingredients\s+for|best\s+pizza|(bake|cook|fry|grill|make)\s+(a\s+)?(pizza|cake|soup|bread|burger|pasta|sandwich|salad|dish|cookie|meal|dessert))\b",
        "Culinary / Food Recipes"
    ),
    # Sports & Athletics
    (
        r"\b(who\s+won\s+the\s+(world\s+cup|super\s+bowl|ipl|match|trophy)|premier\s+league\s+table|nba\s+finals|cricket\s+score)\b",
        "Sports & Athletics"
    ),
    # Celebrity & Entertainment Gossip
    (
        r"\b(celebrity\s+gossip|movie\s+box\s+office|hollywood\s+rumors|actor\s+dating|box\s+office\s+collection)\b",
        "Celebrity & Entertainment Gossip"
    ),
    # Pop Culture & Superheroes / Gaming
    (
        r"\b(who\s+is\s+(spiderman|batman|superman|iron\s+man|goku|naruto|thanos)|avengers\s+endgame|marvel\s+vs\s+dc)\b",
        "Pop Culture & Entertainment"
    ),
    # Astrology & Occult
    (
        r"\b(horoscope|zodiac\s+sign|astrology\s+reading|tarot\s+card|fortune\s+telling)\b",
        "Astrology & Occult"
    ),
    # Medical Advice
    (
        r"\b(how\s+to\s+cure\s+cancer|medical\s+diagnosis|prescription\s+drug|blood\s+pressure\s+medication)\b",
        "Medical Advice"
    ),
    # Casual Chitchat & Creative Writing
    (
        r"\b(tell\s+me\s+a\s+(joke|riddle|story|bedtime\s+story)|make\s+me\s+laugh|sing\s+(a\s+)?song|write\s+(a\s+)?poem|compose\s+(a\s+)?rap)\b",
        "Chitchat / Creative Writing"
    ),
    (
        r"^(how\s+are\s+you(\s+doing)?|who\s+are\s+you|what('?s|\s+is)\s+your\s+name|are\s+you\s+(an?\s+ai|human|real)|do\s+you\s+love\s+me|what('?s|\s+is)\s+the\s+meaning\s+of\s+life)[\?\.\!\s]*$",
        "Casual Chitchat"
    ),
    # Weather & Real-time Info
    (
        r"\b(what('?s|\s+is)\s+the\s+weather|temperature\s+(today|tomorrow|in)|will\s+it\s+rain|weather\s+forecast)\b",
        "Weather Forecast"
    ),
    (
        r"^(what\s+time\s+is\s+it|what\s+is\s+the\s+date|what\s+day\s+is\s+it)[\?\.\!\s]*$",
        "Real-time Date/Time"
    ),
    # Geography & General Trivia
    (
        r"\b(capital\s+of\s+[a-z]+|tallest\s+mountain\s+in\s+the\s+world|longest\s+river|seven\s+wonders\s+of\s+the\s+world|who\s+was\s+the\s+first\s+president\s+of|who\s+invented\s+the\s+(lightbulb|telephone|wheel|airplane))\b",
        "General Trivia / Geography"
    ),
]

# 2. Hard Sciences & Heavy Physical Engineering (Off-bounds unless the candidate's target role is specifically in that field)
PHYSICAL_SCIENCE_PATTERNS = [
    (
        r"\b(thermodynamic[s]?|carnot\s+cycle|carnot\s+efficiency|enthalpy|entropy\s+change|heat\s+engine|adiabatic|isothermal|isochoric|isobaric|refrigerat(ion|or)\s+cycle|fluid\s+mechanic[s]?|aerodynamic[s]?|bernoulli('s)?\s+principle|heat\s+transfer|thermal\s+conductivity)\b",
        "Physics / Thermodynamics"
    ),
    (
        r"\b(internal\s+combustion\s+engine|gear\s+train|kinematics\s+of\s+machiner(y|ies)|finite\s+element\s+analysis\s+of\s+stress|tensile\s+strength\s+testing|cad/cam\s+tooling)\b",
        "Mechanical Engineering"
    ),
    (
        r"\b(soil\s+mechanic[s]?|reinforced\s+concrete\s+slab|beam\s+deflection\s+moment|surveying\s+theodolite|structural\s+civil\s+engineering)\b",
        "Civil Engineering"
    ),
    (
        r"\b(stoichiometr(y|ic)\s+balance|organic\s+chemistr(y|ic)\s+synthesis|distillation\s+column\s+reflux|titration\s+curve)\b",
        "Chemistry / Chemical Engineering"
    ),
    (
        r"\b(photosynthesis|cellular\s+respiration|dna\s+replication\s+fork|pharmacology\s+pathway|human\s+anatomy)\b",
        "Biology / Medicine"
    ),
    (
        r"\b(solar\s+system|how\s+many\s+planets|distance\s+to\s+(the\s+)?(sun|moon|mars)|black\s+hole\s+event\s+horizon|speed\s+of\s+light)\b",
        "Astronomy / Space Trivia"
    ),
]


def check_domain_guardrail(
    query: str,
    active_role: Optional[str] = None,
    topic: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Evaluates whether an inquiry is outside the domain of the candidate's active target role.
    
    If the candidate's active target role is a non-tech role (e.g. Marketing, Product, Sales, HR, Business),
    inquiries relevant to that role/field are strictly IN-BOUND.
    
    Inquiries completely out of bounds (such as 'whats water', thermodynamics/physics for a marketing or software role,
    cooking recipes, sports, entertainment) trigger Tier 3 Domain Guardrail.
    
    Returns:
        (is_out_of_bounds, reason)
    """
    clean_query = query.strip()
    text_to_check = f"{clean_query} {topic or ''}".lower()
    role_str = (active_role or "").lower()

    # 1. Universal off-topic check (always out of bounds)
    for pattern, reason in UNIVERSAL_OFF_TOPIC_PATTERNS:
        if re.search(pattern, clean_query, re.IGNORECASE) or re.search(pattern, text_to_check, re.IGNORECASE):
            return True, reason

    # 2. Hard physical sciences & non-CS engineering check
    # Allow physical sciences ONLY if the active role specifically mentions mechanical, physics, civil, chemical, etc.
    is_physical_engineering_role = any(
        kw in role_str for kw in ["mechanical", "thermal", "physics", "chemical", "civil", "aerospace", "materials", "geology", "astronomy"]
    )
    if not is_physical_engineering_role:
        for pattern, reason in PHYSICAL_SCIENCE_PATTERNS:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                role_label = active_role if active_role else "your target role"
                return True, f"{reason} (unrelated to {role_label})"

    return False, None

