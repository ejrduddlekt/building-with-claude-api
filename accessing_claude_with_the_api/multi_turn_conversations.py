from dotenv import load_dotenv
from anthropic import Anthropic


# .env 파일에 있는 ANTHROPIC_API_KEY를 현재 Python 실행 환경에 불러옵니다.
# 이 코드를 실행해야 Anthropic()이 API 키를 자동으로 찾을 수 있습니다.
load_dotenv()

# Claude API에 요청을 보내기 위한 클라이언트 객체입니다.
# 이후 client.messages.create(...) 형태로 Claude에게 메시지를 보냅니다.
client = Anthropic()

# 요청에 사용할 Claude 모델 이름입니다.
# 강의의 모델명이 안 맞을 수 있어, 현재 계정에서 사용 가능한 모델을 사용합니다.
model = "claude-sonnet-4-6"


def add_user_message(messages, text):
    # 사용자가 보낸 문장을 Claude API가 요구하는 메시지 형식으로 만듭니다.
    # role="user"는 이 메시지가 사람의 입력이라는 뜻입니다.
    user_message = {"role": "user", "content": text}

    # 만든 사용자 메시지를 전체 대화 기록 리스트에 추가합니다.
    messages.append(user_message)


def add_assistant_message(messages, text):
    # Claude가 답한 내용을 메시지 형식으로 만듭니다.
    # role="assistant"는 이 메시지가 Claude의 이전 답변이라는 뜻입니다.
    assistant_message = {"role": "assistant", "content": text}

    # Claude의 답변도 저장해야 다음 질문에서 이전 맥락을 이어갈 수 있습니다.
    messages.append(assistant_message)


def chat(messages):
    # Claude API는 이전 요청을 기억하지 않습니다.
    # 그래서 지금까지의 전체 대화 기록(messages)을 매 요청마다 다시 보냅니다.
    message = client.messages.create(
        model=model,

        # 응답이 너무 길어지는 것을 막는 최대 토큰 제한입니다.
        max_tokens=1000,

        # 지금까지 누적한 user/assistant 메시지 목록입니다.
        messages=messages,
    )

    # message 객체에는 id, 모델명, 토큰 사용량 같은 정보도 들어 있습니다.
    # 여기서는 실제 답변 텍스트만 꺼내서 반환합니다.
    return message.content[0].text


def run():
    # 대화 기록을 저장할 빈 리스트입니다.
    # 이 리스트에 user 메시지와 assistant 메시지를 순서대로 쌓습니다.
    messages = []

    # 첫 번째 사용자 질문을 대화 기록에 추가합니다.
    add_user_message(messages, "Define quantum computing in one sentence")

    # 현재 대화 기록을 Claude에게 보내 첫 번째 답변을 받습니다.
    answer = chat(messages)

    # Claude의 첫 번째 답변을 대화 기록에 추가합니다.
    # 이 작업을 해야 다음 질문에서 "이전 답변"을 맥락으로 사용할 수 있습니다.
    add_assistant_message(messages, answer)

    # 후속 질문을 대화 기록에 추가합니다.
    # 이 질문 자체는 짧지만, messages 안에 이전 문맥이 함께 들어 있습니다.
    add_user_message(messages, "Write another sentence")

    # 전체 대화 기록을 다시 보내므로 Claude가 앞의 주제를 이어서 답할 수 있습니다.
    final_answer = chat(messages)

    # 첫 답변과 후속 답변을 구분해서 터미널에 출력합니다.
    print("First answer:")
    print(answer)
    print()
    print("Follow-up answer:")
    print(final_answer)
