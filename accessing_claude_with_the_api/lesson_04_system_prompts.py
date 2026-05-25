from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()

client = Anthropic()
model = "claude-sonnet-4-6"


def add_user_message(messages, text):
    # 사용자가 입력한 문장을 대화 기록에 추가합니다.
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, text):
    # Claude의 답변을 대화 기록에 추가합니다.
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def chat(messages, system=None):
    # Claude API에 보낼 기본 요청 값입니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
    }

    # system 값이 있으면 요청 값에 추가합니다.
    if system:
        params["system"] = system

    # **params는 딕셔너리를 함수 인자로 풀어서 전달합니다.
    message = client.messages.create(**params)

    return message.content[0].text


def run():
    # 대화 기록을 저장할 리스트입니다.
    messages = []

    # Claude가 어떤 역할과 방식으로 답할지 정하는 지시문입니다.
    system = """
You are a patient math tutor. Do not directly
answer a student's questions. Guide them to a
solution step by step.
"""

    # 사용자 질문을 기록합니다.
    add_user_message(messages, "How do I solve 5x+3=2 for x?")

    # 여기서는 일부러 system을 넘기지 않습니다.
    # chat의 system 기본값이 None이므로 시스템 프롬프트 없이 요청됩니다.
    # 즉, 위에 system 변수를 만들어도 전달하지 않으면 Claude는 그 내용을 모릅니다.
    answer = chat(messages)

    # Claude 답변도 기록해야 다음 대화에서 맥락이 유지됩니다.
    add_assistant_message(messages, answer)

    print(answer)
