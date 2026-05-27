import json
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()

client = Anthropic()

# 데이터셋 생성은 빠른 모델로 충분하므로 Haiku를 사용합니다.
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


def generate_dataset():
    # 프롬프트 평가에 사용할 테스트 작업 3개를 Claude에게 생성시킵니다.
    prompt = """
Generate an evaluation dataset for a prompt evaluation.
The dataset will be used to evaluate prompts that generate Python, JSON, or Regex specifically for AWS-related tasks.
Generate an array of JSON objects, each representing a task that requires Python, JSON, or Regex to complete.

Example output:
```json
[
  {
    "task": "Description of task"
  }
]
```

* Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a single regex.
* Focus on tasks that do not require writing much code.

Please generate 3 objects.
"""

    messages = []
    add_user_message(messages, prompt)

    # JSON 코드블록 안에서 이어 쓰게 만들어 설명 문장을 줄입니다.
    add_assistant_message(messages, "```json")

    # Claude가 코드블록을 닫는 ```를 생성하려 하면 멈춥니다.
    text = chat(messages, stop_sequences=["```"])

    # Claude가 생성한 JSON 문자열을 Python 리스트로 변환합니다.
    return json.loads(text.strip())


def save_dataset(dataset):
    # 이 예제 파일과 같은 폴더에 dataset.json을 저장합니다.
    output_path = Path(__file__).with_name("dataset.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2)

    return output_path


def run():
    # 데이터셋을 생성하고 파일로 저장합니다.
    dataset = generate_dataset()
    output_path = save_dataset(dataset)

    print("Generated dataset:")
    print(json.dumps(dataset, indent=2))
    print()
    print(f"Saved to: {output_path}")
