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


def chat(messages, temperature=1):
    # Claude API에 보낼 기본 요청 값입니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        # temperature는 다음 토큰 선택의 무작위성을 조절합니다.
        # 0에 가까울수록 일관적이고, 1에 가까울수록 다양해집니다.
        "temperature": temperature,
    }

    # **params는 딕셔너리를 함수 인자로 풀어서 전달합니다.
    message = client.messages.create(**params)

    return message.content[0].text


def run():
    # 같은 요청을 여러 번 보내서 temperature 차이를 비교합니다.
    prompt = "Give me one creative name for a coffee shop."

    print("Low temperature: 0")
    print("---")

    # 낮은 temperature는 같은 질문에 더 비슷한 답을 내는 경향이 있습니다.
    for index in range(3):
        messages = []
        add_user_message(messages, prompt)
        answer = chat(messages, temperature=0)
        add_assistant_message(messages, answer)

        print(f"{index + 1}. {answer}")

    print()
    print("High temperature: 1")
    print("---")

    # 높은 temperature는 같은 질문에도 더 다양한 답을 내는 경향이 있습니다.
    for index in range(3):
        messages = []
        add_user_message(messages, prompt)
        answer = chat(messages, temperature=1)
        add_assistant_message(messages, answer)

        print(f"{index + 1}. {answer}")
