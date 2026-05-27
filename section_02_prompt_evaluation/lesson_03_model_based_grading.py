import json
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()

client = Anthropic()

# 프롬프트 실행과 모델 채점 모두 빠른 모델로 먼저 확인합니다.
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

    # system이 있을 때만 요청에 포함합니다.
    if system:
        params["system"] = system

    # stop_sequences가 있을 때만 요청에 포함합니다.
    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    message = client.messages.create(**params)

    return message.content[0].text


def load_dataset():
    # 이전 실습에서 만든 dataset.json을 읽습니다.
    dataset_path = Path(__file__).with_name("dataset.json")

    with dataset_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def run_prompt(test_case):
    # 테스트 케이스의 task를 기본 프롬프트에 넣고 Claude에게 풀이를 요청합니다.
    prompt = f"""
Please solve the following task:

{test_case["task"]}
"""

    messages = []
    add_user_message(messages, prompt)

    return chat(messages)


def grade_by_model(test_case, output):
    # Claude의 답변을 또 다른 Claude 호출로 평가합니다.
    # 점수만 요청하면 애매한 중간 점수로 쏠릴 수 있어 장점/약점/이유도 함께 요청합니다.
    eval_prompt = f"""
You are an expert AWS code reviewer. Your task is to evaluate the following AI-generated solution.

Original Task:
<task>
{test_case["task"]}
</task>

Solution to Evaluate:
<solution>
{output}
</solution>

Evaluation Criteria:
- Format: The answer should return only Python, JSON, or Regex without extra explanation.
- Valid Syntax: The produced code, JSON, or regex should be syntactically valid.
- Task Following: The answer should directly solve the original AWS-related task.

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

    # JSON 코드블록 안에서 이어 쓰게 만들어 평가 결과를 파싱하기 쉽게 합니다.
    add_assistant_message(messages, "```json")

    # Claude가 코드블록을 닫는 ```를 생성하려 하면 멈춥니다.
    eval_text = chat(messages, stop_sequences=["```"])

    # 평가 결과 JSON 문자열을 Python 딕셔너리로 바꿉니다.
    return json.loads(eval_text.strip())


def run_test_case(test_case):
    # 하나의 테스트 케이스를 실행하고, 모델 채점기로 점수를 매깁니다.
    output = run_prompt(test_case)

    model_grade = grade_by_model(test_case, output)
    score = model_grade["score"]
    reasoning = model_grade["reasoning"]

    return {
        "output": output,
        "test_case": test_case,
        "score": score,
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
    # 모델 채점 결과를 별도 파일로 저장합니다.
    output_path = Path(__file__).with_name("model_graded_eval_results.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    return output_path


def run():
    # 전체 실행 흐름입니다.
    # 1. dataset.json을 읽습니다.
    # 2. 각 테스트 케이스에 대해 Claude 답변을 생성합니다.
    # 3. 생성된 답변을 모델 채점기로 평가합니다.
    # 4. 평균 점수와 상세 결과를 저장합니다.
    dataset = load_dataset()
    results = run_eval(dataset)
    output_path = save_results(results)

    print()
    print("Model graded evaluation results:")
    print(json.dumps(results, indent=2))
    print()
    print(f"Saved to: {output_path}")
