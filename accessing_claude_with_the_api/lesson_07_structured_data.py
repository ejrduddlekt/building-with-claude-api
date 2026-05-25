import json

from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()

client = Anthropic()

# 이 실습은 assistant prefill을 사용합니다.
# claude-sonnet-4-6은 prefill을 지원하지 않아 4-5 모델을 사용합니다.
model = "claude-sonnet-4-5-20250929"


def add_user_message(messages, text):
    # 사용자가 입력한 문장을 대화 기록에 추가합니다.
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, text):
    # Claude의 답변을 미리 채워 넣거나 대화 기록에 추가합니다.
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def chat(messages, stop_sequences=None):
    # Claude API에 보낼 기본 요청 값입니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
    }

    # stop_sequences가 있으면 해당 문자열을 만났을 때 생성을 멈춥니다.
    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    # **params는 딕셔너리를 함수 인자로 풀어서 전달합니다.
    message = client.messages.create(**params)

    return message.content[0].text


def run():
    # 대화 기록을 저장할 리스트입니다.
    messages = []

    # Claude에게 JSON 생성을 요청합니다.
    add_user_message(messages, "Generate a very short EventBridge rule as JSON.")

    # assistant 메시지를 미리 채워 Claude가 JSON 코드블록 안에서 이어 쓰게 만듭니다.
    add_assistant_message(messages, "```json")

    # Claude가 코드블록을 닫는 ```를 생성하려 하면 즉시 멈춥니다.
    text = chat(messages, stop_sequences=["```"])

    # Claude의 응답은 일단 "문자열"입니다.
    # 예: '{ "source": ["aws.ec2"] }'
    #
    # text.strip()은 문자열 앞뒤의 공백과 줄바꿈을 제거합니다.
    # JSON 앞뒤에 빈 줄이 있으면 json.loads가 실패할 수 있으므로 정리합니다.
    #
    # json.loads(...)는 JSON 문자열을 Python 데이터로 바꿉니다.
    # 예: 문자열 '{"name": "test"}' -> 딕셔너리 {"name": "test"}
    clean_json = json.loads(text.strip())

    # Claude가 생성한 원본 JSON 문자열을 그대로 출력합니다.
    print("Raw JSON text:")
    print(text.strip())
    print()

    # Python 데이터로 파싱된 JSON을 다시 보기 좋게 들여쓰기해서 출력합니다.
    # indent=2는 중첩된 값마다 공백 2칸으로 정렬하라는 뜻입니다.
    print("Parsed JSON:")
    print(json.dumps(clean_json, indent=2))
