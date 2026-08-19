# Project 2 - Requirements Quality and Gap Analysis Agent

This project is my MSc dissertation prototype for Project 2.

The program checks structured requirements and finds possible quality problems or gaps. It uses a local Large Language Model through LM Studio and saves the review result as a new JSON file.

## What this project does

The program reads a Project 1-style JSON input file and checks the requirements for:

- missing information
- unclear requirements
- incomplete requirements
- missing non-functional requirement metrics
- weak success criteria
- unresolved questions
- vague wording

The final output includes a quality_assurance section with a quality score, detected issues, follow-up questions, and a short summary.

## Tools used

- Python 3
- VS Code
- LM Studio
- OpenAI Python client
- Local model: mistral-7b-instruct-v0.1

## Project files

project2/

- pj2.py
- README.md
- requirements.txt
- prompts/
  - quality_analysis_prompt.txt
  - quality_criteria.txt
- input/
  - hair_salon_input.json
  - hotel_booking_input.json
- outputs/

## Setup

Create a virtual environment:

python -m venv .venv

Activate it.

On Windows:

.venv\Scripts\activate

On Linux or macOS:

source .venv/bin/activate

Install the required package:

pip install -r requirements.txt

## Before running the program

Open LM Studio first.

Then:

1. Load mistral-7b-instruct-v0.1.
2. Start the local server.
3. Make sure the server is running on port 1234.

## How to run

To run the default Hair Salon input:

python pj2.py

To run the Hair Salon input directly:

python pj2.py input/hair_salon_input.json

To run the Hotel Booking input:

python pj2.py input/hotel_booking_input.json

## Input files

The input files are stored in the input folder.

The two sample input files are:

- input/hair_salon_input.json
- input/hotel_booking_input.json

Each input file contains structured requirements in a Project 1-style JSON format.

## Prompt files

The prompt files are stored in the prompts folder.

- prompts/quality_analysis_prompt.txt
- prompts/quality_criteria.txt

The main prompt tells the local LLM what type of requirements quality review to perform. The quality criteria file contains the checklist used to guide the analysis.

## Output files

The output files are saved automatically in the outputs folder.

Example output files:

- outputs/hair_salon_input_project2_output.json
- outputs/hotel_booking_input_project2_output.json

The output JSON includes:

- review status
- quality score
- score breakdown
- detected issues
- follow-up questions
- summary

## Notes

This prototype does not collect requirements from users. It only analyses requirements that are already written in JSON format.

If the LLM does not return valid JSON, the program does not stop. It uses Python fallback checks and still creates an output file.