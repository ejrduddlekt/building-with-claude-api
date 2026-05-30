# Continuation Guide

## Project

Repository:

```text
D:\Develop\Claude\Building-with-claude-api
```

GitHub remote:

```text
https://github.com/ejrduddlekt/building-with-claude-api.git
```

This project follows the Anthropic course "Building with the Claude API".

The user is learning Python while following the course, so examples should be explicit and beginner-friendly. Add comments when the code introduces a new concept, but avoid overly long comments unless the user asks for deeper explanation.

## Current Structure

```text
main.py
.env
.gitignore
summary/
  section_01_summary.md
  section_02_summary.md
  continuation_guide.md
section_01_accessing_claude_with_the_api/
  lesson_01_making_a_request.py
  lesson_02_multi_turn_conversations.py
  lesson_03_chat_exercise.py
  lesson_04_system_prompts.py
  lesson_05_temperature.py
  lesson_06_response_streaming.py
  lesson_07_structured_data.py
  lesson_08_structured_data_exercise.py
section_02_prompt_evaluation/
  lesson_01_generating_test_datasets.py
  lesson_02_running_the_eval.py
  lesson_03_model_based_grading.py
  lesson_04_code_based_grading.py
  lesson_05_complete_eval_with_criteria.py
  dataset/result JSON files
```

Other section folders were created earlier in indexed form:

```text
section_03_prompt_engineering_techniques
section_04_tool_use_with_claude
section_05_rag_and_agentic_search
section_06_features_of_claude
section_07_model_context_protocol
section_08_anthropic_apps_claude_code_and_computer_use
section_09_agents_and_workflows
```

They may be empty until the course reaches them.

## How Examples Are Run

`main.py` imports one lesson's `run()` function.

Example:

```python
from section_02_prompt_evaluation.lesson_05_complete_eval_with_criteria import run

if __name__ == "__main__":
    run()
```

To switch lessons, update only the import in `main.py`.

The project convention is:

- each lesson file has a `run()` function
- most API examples use helper functions like `add_user_message`, `add_assistant_message`, and `chat`
- lesson files are indexed as `lesson_01_...`, `lesson_02_...`
- section folders are indexed as `section_01_...`, `section_02_...`

## Environment

The `.env` file must contain:

```env
ANTHROPIC_API_KEY="..."
```

`.env` is ignored by Git and must not be committed.

Installed packages used so far:

```text
anthropic
python-dotenv
```

Run examples with:

```powershell
python main.py
```

Some examples call Anthropic API and need network/API access.

## Model Notes

The user's account currently had these working model IDs during the session:

```text
claude-sonnet-4-6
claude-haiku-4-5-20251001
claude-sonnet-4-5-20250929
```

Important:

- `claude-sonnet-4-6` worked for normal requests.
- Assistant prefill was not supported by `claude-sonnet-4-6`.
- Prefill examples use `claude-sonnet-4-5-20250929`.
- Prompt evaluation examples use `claude-haiku-4-5-20251001`.

## Completed Course Content

Section 01 completed examples:

1. Making a request
2. Multi-turn conversations
3. Chat exercise
4. System prompts
5. Temperature
6. Response streaming
7. Structured data
8. Structured data exercise

Section 02 completed examples:

1. Generating test datasets
2. Running the eval
3. Model based grading
4. Code based grading
5. Complete eval with `solution_criteria`

Summary files for review:

- `summary/section_01_summary.md`
- `summary/section_02_summary.md`

## Teaching Style That Worked

The user prefers:

- concise explanations first
- more detail when explicitly requested
- comments that explain why code exists, not every obvious token
- Python concepts compared to C# when helpful
- maintaining a consistent default structure:

```python
def add_user_message(messages, text):
    ...

def add_assistant_message(messages, text):
    ...

def chat(...):
    ...

def run():
    ...
```

The user is still learning Python, so explain:

- imports and folder/module paths
- `with open(...)`
- `json.load` vs `json.loads`
- `json.dump` vs `json.dumps`
- `**params`
- `if __name__ == "__main__"`
- lists, dictionaries, and `append`

## Git Status At Handoff

Before continuing, run:

```powershell
git status -sb
```

The summary files were created after the last push and may not yet be committed.

Last pushed commit during the session:

```text
3d3fd11 Add prompt evaluation lessons
```

If the user asks to push, include:

```text
summary/
```

and verify `.env` is not staged.

## Next Likely Step

The course appears ready to move into:

```text
section_03_prompt_engineering_techniques
```

When adding new examples:

1. Add files under `section_03_prompt_engineering_techniques`.
2. Use indexed lesson filenames.
3. Update `main.py` to import the newest lesson.
4. Run `python -m py_compile ...`.
5. If API code is involved, run `python main.py`.
6. Push only when the user asks.
