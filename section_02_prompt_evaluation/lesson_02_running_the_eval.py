import json
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()

client = Anthropic()

# 평가 실행도 빠른 모델로 먼저 확인합니다.
model = "claude-haiku-4-5-20251001"


def add_user_message(messages, text):
    # 사용자가 입력한 문장을 대화 기록에 추가합니다.
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


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
    # 이 파일에는 [{"task": "..."}] 형태의 테스트 케이스들이 들어 있습니다.
    dataset_path = Path(__file__).with_name("dataset.json")

    with dataset_path.open("r", encoding="utf-8") as file:
        # json.load는 JSON 파일 내용을 Python 리스트/딕셔너리로 바꿉니다.
        return json.load(file)


def run_prompt(test_case):
    # 평가 파이프라인의 첫 단계입니다.
    # 하나의 test_case를 받아 실제 Claude에게 보낼 프롬프트를 만듭니다.
    #
    # test_case 예:
    # {"task": "Create a JSON object for an S3 IAM policy"}
    prompt = f"""
Please solve the following task:

{test_case["task"]}
"""

    messages = []
    add_user_message(messages, prompt)

    # 현재는 아주 단순한 프롬프트라 Claude가 설명까지 길게 답할 수 있습니다.
    # 이후 강의에서 이 프롬프트를 개선하고 결과가 좋아지는지 평가합니다.
    output = chat(messages)

    return output


def run_test_case(test_case):
    # 평가 파이프라인의 두 번째 단계입니다.
    # 하나의 테스트 케이스를 실행하고, 그 결과를 채점 가능한 형태로 묶습니다.
    output = run_prompt(test_case)

    # 아직 실제 채점 로직은 없으므로 임시로 10점을 넣습니다.
    # 다음 강의에서 model grader 또는 code grader로 이 부분을 교체합니다.
    score = 10

    # 한 테스트 케이스에 대한 결과를 딕셔너리로 정리합니다.
    # output: Claude가 생성한 답변
    # test_case: 어떤 입력으로 실행했는지
    # score: 이 답변의 점수
    return {
        "output": output,
        "test_case": test_case,
        "score": score,
    }


def run_eval(dataset):
    # 평가 파이프라인의 세 번째 단계입니다.
    # 데이터셋 전체를 돌면서 각 테스트 케이스를 실행합니다.
    results = []

    for test_case in dataset:
        # 테스트 케이스 하나를 실행하고 결과를 받습니다.
        result = run_test_case(test_case)

        # 전체 평가 결과 목록에 누적합니다.
        results.append(result)

    return results


def save_results(results):
    # 평가 결과를 나중에 확인할 수 있도록 JSON 파일로 저장합니다.
    # 이렇게 저장해두면 프롬프트를 바꿨을 때 이전 결과와 비교할 수 있습니다.
    output_path = Path(__file__).with_name("eval_results.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    return output_path


def run():
    # 전체 실행 흐름입니다.
    # 1. dataset.json을 읽습니다.
    # 2. 모든 테스트 케이스를 Claude에게 보냅니다.
    # 3. 결과를 eval_results.json으로 저장합니다.
    dataset = load_dataset()
    results = run_eval(dataset)
    output_path = save_results(results)

    print("Evaluation results:")
    print(json.dumps(results, indent=2))
    print()
    print(f"Saved to: {output_path}")
