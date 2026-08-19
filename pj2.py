import json
import os
import sys
from datetime import datetime
from openai import OpenAI


# Default files and folders
INPUT_FILE = "input/hair_salon_input.json"
OUTPUT_FOLDER = "outputs"
PROMPT_FILE = "prompts/quality_analysis_prompt.txt"
QUALITY_CRITERIA_FILE = "prompts/quality_criteria.txt"


# Connect to the local LM Studio server
client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)


# Main sections expected in the Project 1-style JSON file
REQUIRED_SECTIONS = [
    "goals_and_objectives",
    "stakeholders",
    "functional_requirements",
    "non_functional_requirements",
    "data_requirements",
    "constraints",
    "success_criteria",
    "risks",
    "assumptions",
    "unresolved_questions"
]


# Words that can make requirements unclear or hard to measure
VAGUE_WORDS = [
    "easy",
    "quickly",
    "fast",
    "secure",
    "reliable",
    "simple",
    "good",
    "accurate",
    "user-friendly"
]


def get_input_file():
    # Use the file path from the terminal if one is provided
    if len(sys.argv) > 1:
        return sys.argv[1]

    # Otherwise, use the default Hair Salon input file
    return INPUT_FILE


def get_output_file(input_file):
    # Create an output filename based on the input filename
    name = os.path.splitext(os.path.basename(input_file))[0]
    return os.path.join(OUTPUT_FOLDER, name + "_project2_output.json")


def load_json(file_path):
    # Read the input JSON file
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_text_file(file_path):
    # Read a text file such as the prompt or checklist
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def save_json(data, file_path):
    # Create the output folder if it does not exist
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Save the reviewed JSON output
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print("\nJSON output saved to:", file_path)


def make_issue(requirement_id, issue_type, severity, note, question):
    # Keep all detected issues in the same structure
    return {
        "requirement_id": str(requirement_id),
        "type": str(issue_type),
        "severity": str(severity),
        "note": str(note),
        "follow_up_question": str(question)
    }


def build_prompt(data):
    # Build the final prompt using the external prompt and checklist files
    prompt_template = load_text_file(PROMPT_FILE)
    quality_criteria = load_text_file(QUALITY_CRITERIA_FILE)

    requirements_json = json.dumps(
        data.get("requirements", {}),
        indent=2,
        ensure_ascii=False
    )

    prompt = prompt_template.replace("{quality_criteria}", quality_criteria)
    prompt = prompt.replace("{requirements_json}", requirements_json)

    return prompt


def extract_json(text):
    # Try to read the LLM response as JSON
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # If the LLM adds extra text, try to extract only the JSON object
        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON object found.")

        return json.loads(text[start:end])


def validate_llm_output(result):
    # Check that the main LLM output fields exist
    required_fields = ["status", "overall_quality_score", "issues", "summary"]

    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing field: {field}")

    if not isinstance(result["issues"], list):
        raise ValueError("issues must be a list.")

    if not isinstance(result["summary"], str) or result["summary"].strip() == "":
        raise ValueError("summary must not be empty.")

    # Check that every issue contains the fields needed by the program
    required_issue_fields = [
        "requirement_id",
        "type",
        "severity",
        "note",
        "follow_up_question"
    ]

    for issue in result["issues"]:
        for field in required_issue_fields:
            if field not in issue or str(issue[field]).strip() == "":
                raise ValueError(f"Issue field missing or empty: {field}")


def ask_llm(data):
    # Build the prompt from the external prompt files
    prompt = build_prompt(data)

    # Use the model currently loaded in LM Studio
    model = client.models.list().data[0].id
    print("Using model:", model)

    last_error = ""

    # Retry because the local LLM may not always return valid JSON
    for attempt in range(1, 4):
        print(f"\nLLM attempt {attempt}/3")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON. Do not use markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=1500
        )

        raw_output = response.choices[0].message.content

        try:
            result = extract_json(raw_output)
            validate_llm_output(result)

            print("\n--- RAW LLM OUTPUT ---\n")
            print(raw_output)

            return result

        except Exception as error:
            last_error = error

    # If the LLM fails after retries, Python fallback checks will still run
    print("\n--- RAW LLM OUTPUT ---\n")
    print("LLM failed to return useful valid JSON.")
    print("Using Python fallback analysis.")
    print("LLM error:", last_error)

    return None


def has_vague_word(text):
    # Check if a requirement contains a vague word
    if not isinstance(text, str):
        return None

    text = text.lower()

    for word in VAGUE_WORDS:
        if word in text:
            return word

    return None


def rule_based_checks(data):
    # Python checks help the program still work when the LLM output fails
    requirements = data.get("requirements", {})
    issues = []

    # Check for missing main sections
    for section in REQUIRED_SECTIONS:
        if section not in requirements:
            issues.append(
                make_issue(
                    section,
                    "missing_section",
                    "high",
                    f"The requirements are missing the {section} section.",
                    f"What information should be added to {section}?"
                )
            )

    # Check non-functional requirements
    for nfr in requirements.get("non_functional_requirements", []):
        req_id = nfr.get("id", "unknown")
        statement = nfr.get("statement", "")

        if not nfr.get("metric"):
            severity = "high" if nfr.get("category") == "security" else "medium"

            issues.append(
                make_issue(
                    req_id,
                    "missing_metric",
                    severity,
                    f"The non-functional requirement '{statement}' has no measurable metric.",
                    f"What measurable target should be used for {req_id}?"
                )
            )

        vague_word = has_vague_word(statement)

        if vague_word:
            issues.append(
                make_issue(
                    req_id,
                    "vague_wording",
                    "medium",
                    f"The requirement uses vague wording: '{vague_word}'.",
                    f"How should '{vague_word}' be defined or measured for {req_id}?"
                )
            )

    # Check success criteria
    for sc in requirements.get("success_criteria", []):
        sc_id = sc.get("id", "unknown")
        statement = sc.get("statement", "")

        if not sc.get("target"):
            issues.append(
                make_issue(
                    sc_id,
                    "missing_target",
                    "medium",
                    f"The success criterion '{statement}' has no target value.",
                    f"What target value should be used for {sc_id}?"
                )
            )

    # Add open unresolved questions to the issue list
    for question in requirements.get("unresolved_questions", []):
        if question.get("status") == "open":
            issues.append(
                make_issue(
                    question.get("id", "unknown"),
                    "unresolved_question",
                    "medium",
                    "There is still an open unresolved question.",
                    question.get("question", "What information is still unresolved?")
                )
            )

    return issues


def normalise_llm_issues(llm_result):
    # Convert LLM issues into the same format as Python issues
    issues = []

    for issue in llm_result.get("issues", []):
        issues.append(
            make_issue(
                issue.get("requirement_id", "unknown"),
                issue.get("type", "llm_detected_issue"),
                issue.get("severity", "medium"),
                issue.get("note", ""),
                issue.get("follow_up_question", "")
            )
        )

    return issues


def remove_duplicate_issues(issues):
    # Remove repeated issues before saving the output
    clean = []
    seen = set()

    for issue in issues:
        key = (
            issue["requirement_id"],
            issue["type"],
            issue["follow_up_question"]
        )

        if key not in seen:
            seen.add(key)
            clean.append(issue)

    return clean


def calculate_score(data, issues):
    # Calculate the quality score using section completeness and issue penalties
    requirements = data.get("requirements", {})
    completed_sections = 0

    for section in REQUIRED_SECTIONS:
        if isinstance(requirements.get(section), list) and len(requirements[section]) > 0:
            completed_sections += 1

    section_score = completed_sections / len(REQUIRED_SECTIONS)
    penalty = 0

    # Higher severity issues reduce the score more
    for issue in issues:
        if issue["severity"] == "high":
            penalty += 0.08
        elif issue["severity"] == "medium":
            penalty += 0.04
        else:
            penalty += 0.02

    penalty = min(penalty, 0.8)
    final_score = (section_score * 0.4) + ((1 - penalty) * 0.6)

    return round(final_score, 2), round(section_score, 2), round(penalty, 2)


def decide_status(score):
    # Convert the score into a review status
    if score >= 0.85:
        return "ready_for_next_stage"

    if score >= 0.70:
        return "needs_more_information"

    return "needs_major_revision"


def build_quality_assurance(data, issues, llm_used):
    # Build the final quality_assurance section
    score, section_score, penalty = calculate_score(data, issues)
    project_title = data.get("metadata", {}).get("project_title", "the project")

    return {
        "status": decide_status(score),
        "reviewed_by": "project_2",
        "reviewed_at": datetime.now().isoformat(timespec="seconds"),
        "overall_quality_score": score,
        "score_breakdown": {
            "section_completeness_score": section_score,
            "issue_penalty": penalty,
            "total_issues": len(issues)
        },
        "analysis_method": "local_llm_with_python_guardrails",
        "llm_status": "llm_output_used" if llm_used else "llm_failed_rule_based_used",
        "issues": issues,
        "summary": (
            f"The requirements for {project_title} received a quality score of {score}. "
            f"The system found {len(issues)} issue(s). "
            f"The analysis used {'LLM output and rule-based checks' if llm_used else 'rule-based fallback checks because the LLM output failed validation'}."
        )
    }


def check_final_output(quality_assurance):
    # Final guardrail check before saving
    if "overall_quality_score" not in quality_assurance:
        return False

    if "issues" not in quality_assurance:
        return False

    if "summary" not in quality_assurance:
        return False

    if not isinstance(quality_assurance["issues"], list):
        return False

    return True


def main():
    # Get input and output paths
    input_file = get_input_file()
    output_file = get_output_file(input_file)

    print("Input file:", input_file)
    print("Output file:", output_file)

    # Load input JSON
    data = load_json(input_file)

    # Ask the LLM first, then run Python checks
    llm_result = ask_llm(data)
    issues = rule_based_checks(data)

    # Use LLM issues only if the LLM output passed validation
    if llm_result is not None:
        issues = issues + normalise_llm_issues(llm_result)
        llm_used = True
    else:
        llm_used = False

    # Remove repeated issues
    issues = remove_duplicate_issues(issues)

    # Keep human review as a safety reminder if no issue is found
    if len(issues) == 0:
        issues.append(
            make_issue(
                "general",
                "review_needed",
                "low",
                "No major issue was detected, but human review is still recommended.",
                "Are there any missing business rules or edge cases?"
            )
        )

    # Create final Project 2 result
    quality_assurance = build_quality_assurance(data, issues, llm_used)

    print("\n--- GUARDRAIL RESULT ---")

    if check_final_output(quality_assurance):
        print("Output passed guardrail check.")
    else:
        print("Output failed guardrail check.")

    # Save Project 2 output back into the shared JSON structure
    data["quality_assurance"] = quality_assurance
    data["current_stage"] = "project_2_complete"

    data.setdefault("pipeline_history", [])
    data["pipeline_history"].append(
        {
            "stage": "project_2",
            "status": quality_assurance["status"],
            "timestamp": quality_assurance["reviewed_at"],
            "message": "Requirements reviewed by Project 2 quality and gap analysis prototype."
        }
    )

    save_json(data, output_file)


if __name__ == "__main__":
    main()