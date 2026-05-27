import ast
import json
import re
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()

client = Anthropic()

# 이 예제는 평가 파이프라인 구조를 보는 것이 목적이라 빠른 Haiku 모델을 사용합니다.
model = "claude-haiku-4-5-20251001"


def add_user_message(messages, text):
    # 사용자가 보낸 메시지를 Claude API 형식으로 대화 기록에 추가합니다.
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, text):
    # Claude가 이미 답변을 시작한 것처럼 assistant 메시지를 미리 넣습니다.
    # JSON만 받거나 코드블록 안쪽만 받게 만들 때 사용합니다.
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None):
    # Claude API 호출에 필요한 공통 파라미터를 먼저 딕셔너리로 만듭니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature,
    }

    # system prompt가 필요한 호출에서만 추가합니다.
    if system:
        params["system"] = system

    # stop sequence가 필요한 호출에서만 추가합니다.
    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    message = client.messages.create(**params)

    return message.content[0].text


def generate_dataset():
    # 이번 챕터의 핵심은 solution_criteria입니다.
    #
    # 이전 dataset:
    #   task: 무엇을 만들지
    #   format: python/json/regex 중 무엇을 기대하는지
    #
    # 이번 dataset:
    #   solution_criteria: 좋은 답변인지 판단할 구체적인 기준
    #
    # 즉, 채점 모델에게 "이 기준으로 평가해"라고 넘겨줄 재료를 dataset에 같이 저장합니다.
    prompt = """
Generate an evaluation dataset for a prompt evaluation.
The dataset will be used to evaluate prompts that generate Python, JSON, or Regex specifically for AWS-related tasks.
Generate an array of JSON objects, each representing a task that requires Python, JSON, or Regex to complete.

Example output:
```json
[
  {
    "task": "Description of task",
    "format": "json" or "python" or "regex",
    "solution_criteria": "Key criteria for evaluating the solution"
  }
]
```

* Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a single regex.
* Focus on tasks that do not require writing much code.
* Make sure one task uses "python", one uses "json", and one uses "regex".
* Write solution_criteria as concrete checks the grader can use.

Please generate 3 objects.
"""

    messages = []
    add_user_message(messages, prompt)

    # 데이터셋은 JSON 배열이어야 하므로 JSON 코드블록을 prefill합니다.
    add_assistant_message(messages, "```json")

    # Claude가 코드블록을 닫으려는 순간 멈춰 JSON 본문만 받습니다.
    text = chat(messages, stop_sequences=["```"])

    return json.loads(text.strip())


def save_dataset(dataset):
    # solution_criteria가 포함된 완성형 데이터셋을 별도 파일로 저장합니다.
    output_path = Path(__file__).with_name("complete_eval_dataset.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2)

    return output_path


def run_prompt(test_case):
    # 실제로 평가할 대상 답변을 만드는 함수입니다.
    #
    # 이 프롬프트는 일부러 아주 완벽하지는 않습니다.
    # 그래야 평가기가 "형식이 틀렸다", "설명이 붙었다" 같은 문제를 잡아낼 수 있습니다.
    prompt = f"""
Please solve the following task:

{test_case["task"]}

* Respond only with Python, JSON, or a plain Regex.
* Do not add any comments or commentary or explanation.
"""

    messages = []
    add_user_message(messages, prompt)

    # 코드블록 안에서 이어 쓰게 만들어 설명 문장을 줄입니다.
    add_assistant_message(messages, "```code")

    return chat(messages, stop_sequences=["```"])


def grade_by_model(test_case, output):
    # 모델 채점기는 코드 문법만 보는 것이 아니라 "과제를 제대로 해결했는지"를 평가합니다.
    #
    # 이번 챕터에서 중요한 점:
    # test_case["solution_criteria"]를 채점 프롬프트에 넣습니다.
    # 그러면 채점 모델이 막연히 평가하지 않고, dataset에 적힌 구체적인 기준으로 평가합니다.
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

Criteria you should use to evaluate the solution:
<criteria>
{test_case["solution_criteria"]}
</criteria>

Output Format:
Provide your evaluation as a structured JSON object with these fields:
- "strengths": An array of 1-3 key strengths
- "weaknesses": An array of 1-3 key areas for improvement
- "reasoning": A concise explanation of your overall assessment
- "score": A number between 1 and 10

Respond with JSON only.
"""

    messages = []
    add_user_message(messages, eval_prompt)

    # 평가 결과도 JSON으로 파싱해야 하므로 JSON 코드블록을 prefill합니다.
    add_assistant_message(messages, "```json")

    eval_text = chat(messages, stop_sequences=["```"])

    return json.loads(eval_text.strip())


def validate_json(text):
    # JSON 문법 검사입니다. 파싱에 성공하면 10점, 실패하면 0점입니다.
    try:
        json.loads(text.strip())
        return 10
    except json.JSONDecodeError:
        return 0


def validate_python(text):
    # Python 문법 검사입니다.
    # ast.parse는 코드를 실행하지 않고 문법 구조만 확인합니다.
    try:
        ast.parse(text.strip())
        return 10
    except SyntaxError:
        return 0


def validate_regex(text):
    # Regex 문법 검사입니다.
    # re.compile이 성공하면 정규식 문법은 유효하다고 봅니다.
    try:
        re.compile(text.strip())
        return 10
    except re.error:
        return 0


def grade_syntax(response, test_case):
    # format 값에 따라 어떤 문법 검사 함수를 사용할지 결정합니다.
    expected_format = test_case["format"]

    if expected_format == "json":
        return validate_json(response)
    if expected_format == "python":
        return validate_python(response)

    return validate_regex(response)


def run_test_case(test_case):
    # 하나의 테스트 케이스를 평가하는 전체 흐름입니다.
    #
    # 1. run_prompt로 Claude 답변 생성
    # 2. grade_by_model로 의미/정확성 평가
    # 3. grade_syntax로 형식/문법 평가
    # 4. 두 점수의 평균을 최종 점수로 계산
    output = run_prompt(test_case)

    model_grade = grade_by_model(test_case, output)
    model_score = model_grade["score"]
    syntax_score = grade_syntax(output, test_case)

    score = (model_score + syntax_score) / 2

    return {
        "output": output,
        "test_case": test_case,
        "score": score,
        "model_score": model_score,
        "syntax_score": syntax_score,
        "reasoning": model_grade["reasoning"],
        "strengths": model_grade["strengths"],
        "weaknesses": model_grade["weaknesses"],
    }


def run_eval(dataset):
    # 데이터셋 전체를 순회하면서 각 테스트 케이스를 평가합니다.
    results = []

    for test_case in dataset:
        result = run_test_case(test_case)
        results.append(result)

    average_score = mean([result["score"] for result in results])
    print(f"Average score: {average_score}")

    return results


def save_results(results):
    # 완성형 평가 결과를 별도 파일로 저장합니다.
    output_path = Path(__file__).with_name("complete_eval_results.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    return output_path


def run():
    # 전체 실행 흐름입니다.
    #
    # 1. solution_criteria가 포함된 dataset 생성
    # 2. 각 task에 대해 Claude 답변 생성
    # 3. solution_criteria 기준으로 모델 채점
    # 4. format 기준으로 코드 문법 채점
    # 5. 최종 결과 저장
    dataset = generate_dataset()
    dataset_path = save_dataset(dataset)

    results = run_eval(dataset)
    results_path = save_results(results)

    print()
    print(f"Dataset saved to: {dataset_path}")
    print(f"Results saved to: {results_path}")
    print()
    print("Complete evaluation results:")
    print(json.dumps(results, indent=2))
