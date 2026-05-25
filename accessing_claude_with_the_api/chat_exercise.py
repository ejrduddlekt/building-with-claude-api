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


def chat(messages):
    # 지금까지의 전체 대화 기록을 Claude에게 보냅니다.
    message = client.messages.create(
        model=model,
        max_tokens=1000,
        messages=messages,
    )

    return message.content[0].text


def run():
    # 대화 기록을 저장할 리스트입니다.
    messages = []

    print("Claude chat started. Type 'exit' or 'quit' to stop.")

    # 사용자가 종료할 때까지 계속 입력을 받습니다.
    while True:
        user_input = input("> ")

        # 빈 입력은 무시합니다.
        if not user_input.strip():
            continue

        # exit 또는 quit을 입력하면 챗을 종료합니다.
        if user_input.lower() in ["exit", "quit"]:
            print("Chat ended.")
            break

        # 사용자 입력을 기록하고 Claude에게 보냅니다.
        add_user_message(messages, user_input)
        answer = chat(messages)

        # Claude 답변도 기록해야 다음 대화에서 맥락이 유지됩니다.
        add_assistant_message(messages, answer)

        print("---")
        print(answer)
