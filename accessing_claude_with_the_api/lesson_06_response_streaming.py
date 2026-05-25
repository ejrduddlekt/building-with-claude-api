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


def stream_chat(messages):
    # 응답을 한 번에 기다리지 않고 텍스트 조각이 생길 때마다 받습니다.
    with client.messages.stream(
        model=model,
        max_tokens=1000,
        messages=messages,
    ) as stream:
        # text_stream은 실제 텍스트 조각만 골라서 순서대로 돌려줍니다.
        for text in stream.text_stream:
            print(text, end="")

        # 스트리밍이 끝난 뒤에는 완성된 메시지 객체를 얻을 수 있습니다.
        final_message = stream.get_final_message()

    return final_message.content[0].text


def run():
    # 대화 기록을 저장할 리스트입니다.
    messages = []

    add_user_message(
        messages,
        "Write a 1 sentence description of a fake database.",
    )

    print("Streaming answer:")
    print("---")

    # Claude 응답이 생성되는 동안 터미널에 바로바로 출력됩니다.
    answer = stream_chat(messages)

    # 전체 응답도 대화 기록에 저장할 수 있습니다.
    add_assistant_message(messages, answer)

    print()
    print("---")
    print("Final message saved to conversation history.")
