import ast
import json
import re
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()

client = Anthropic()

# 프롬프트 실행, 데이터셋 생성, 채점 모두 빠른 모델로 먼저 확인합니다.
model = "claude-haiku-4-5-20251001"


def add_user_message(messages, text):
    # 사용자가 입력한 문장을 대화 기록에 추가합니다.
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, text):
    # Claude의 답변 시작 부분을 미리 채워 넣습니다.
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None):
    # Claude API에 보낼 기본 요청 값입니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature,
    }

    if system:
        params["system"] = system

    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    message = client.messages.create(**params)

    return message.content[0].text


def generate_dataset():
    # 코드 채점기는 어떤 검증 함수를 쓸지 알아야 하므로 format 필드가 필요합니다.
    prompt = """
Generate an evaluation dataset for a prompt evaluation.
The dataset will be used to evaluate prompts that generate Python, JSON, or Regex specifically for AWS-related tasks.
Generate an array of JSON objects, each representing a task that requires Python, JSON, or Regex to complete.

Example output:
```json
[
  {
    "task": "Description of task",
    "format": "json" or "python" or "regex"
  }
]
```

* Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a single regex.
* Focus on tasks that do not require writing much code.
* Make sure one task uses "python", one uses "json", and one uses "regex".

Please generate 3 objects.
"""

    messages = []
    add_user_message(messages, prompt)
    add_assistant_message(messages, "```json")

    text = chat(messages, stop_sequences=["```"])

    return json.loads(text.strip())


def save_dataset(dataset):
    # format 필드가 들어 있는 코드 채점용 데이터셋을 따로 저장합니다.
    output_path = Path(__file__).with_name("code_grading_dataset.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2)

    return output_path


def grade_by_model(test_case, output):
    # 모델 채점기는 "과제를 잘 해결했는지"처럼 코드로 판단하기 어려운 부분을 봅니다.
    eval_prompt = f"""
You are an expert AWS code reviewer. Your task is to evaluate the following AI-generated solution.

Original Task:
<task>
{test_case["task"]}
</task>

Expected Format:
<format>
{test_case["format"]}
</format>

Solution to Evaluate:
<solution>
{output}
</solution>

Evaluation Criteria:
- Task Following: The answer should directly solve the original AWS-related task.
- Correctness: The answer should be accurate for AWS usage.
- Minimality: The answer should avoid unnecessary explanation or extra content.

Output Format:
Provide your evaluation as a structured JSON object with these fields:
- "strengths": An array of 1-3 key strengths
- "weaknesses": An array of 1-3 key areas for improvement
- "reasoning": A concise explanation of your assessment
- "score": A number between 1 and 10

Respond with JSON only.
"""

    messages = []
    add_user_message(messages, eval_prompt)
    add_assistant_message(messages, "```json")

    eval_text = chat(messages, stop_sequences=["```"])

    return json.loads(eval_text.strip())


def run_prompt(test_case):
    # 출력 형식을 더 엄격히 지시해서 코드 채점기가 검증하기 쉽게 만듭니다.
    prompt = f"""
Please solve the following task:

{test_case["task"]}

* Respond only with Python, JSON, or a plain Regex.
* Do not add any comments, commentary, or explanation.
"""

    messages = []
    add_user_message(messages, prompt)

    # 코드블록 안에서 이어 쓰게 만들어 설명 문장을 줄입니다.
    add_assistant_message(messages, "```code")

    output = chat(messages, stop_sequences=["```"])

    return output


def validate_json(text):
    # JSON으로 파싱되면 문법 점수 10점, 실패하면 0점입니다.
    try:
        json.loads(text.strip())
        return 10
    except json.JSONDecodeError:
        return 0


def validate_python(text):
    # ast.parse는 Python 코드를 실행하지 않고 문법만 검사합니다.
    try:
        ast.parse(text.strip())
        return 10
    except SyntaxError:
        return 0


def validate_regex(text):
    # re.compile은 정규식 문법이 유효한지 확인합니다.
    try:
        re.compile(text.strip())
        return 10
    except re.error:
        return 0


def grade_syntax(response, test_case):
    # test_case의 format 값에 맞는 검증 함수를 선택합니다.
    expected_format = test_case["format"]

    if expected_format == "json":
        return validate_json(response)
    if expected_format == "python":
        return validate_python(response)

    return validate_regex(response)


def run_test_case(test_case):
    # 하나의 테스트 케이스를 실행하고 모델 점수와 문법 점수를 함께 계산합니다.
    output = run_prompt(test_case)

    model_grade = grade_by_model(test_case, output)
    model_score = model_grade["score"]
    reasoning = model_grade["reasoning"]

    syntax_score = grade_syntax(output, test_case)

    # 최종 점수는 의미 품질과 문법 유효성을 같은 비중으로 평균냅니다.
    score = (model_score + syntax_score) / 2

    return {
        "output": output,
        "test_case": test_case,
        "score": score,
        "model_score": model_score,
        "syntax_score": syntax_score,
        "reasoning": reasoning,
        "strengths": model_grade["strengths"],
        "weaknesses": model_grade["weaknesses"],
    }


def run_eval(dataset):
    # 데이터셋 전체를 실행하고 평균 점수를 계산합니다.
    results = []

    for test_case in dataset:
        result = run_test_case(test_case)
        results.append(result)

    average_score = mean([result["score"] for result in results])
    print(f"Average score: {average_score}")

    return results


def save_results(results):
    # 코드 채점 결과를 별도 파일로 저장합니다.
    output_path = Path(__file__).with_name("code_graded_eval_results.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    return output_path


def run():
    # 전체 실행 흐름입니다.
    # 1. format 필드가 포함된 데이터셋을 생성합니다.
    # 2. 각 테스트 케이스에 대해 Claude 답변을 생성합니다.
    # 3. 모델 채점과 코드 문법 채점을 모두 수행합니다.
    # 4. 두 점수의 평균을 최종 점수로 저장합니다.
    dataset = generate_dataset()
    dataset_path = save_dataset(dataset)

    results = run_eval(dataset)
    results_path = save_results(results)

    print()
    print(f"Dataset saved to: {dataset_path}")
    print(f"Results saved to: {results_path}")
    print()
    print("Code graded evaluation results:")
    print(json.dumps(results, indent=2))
