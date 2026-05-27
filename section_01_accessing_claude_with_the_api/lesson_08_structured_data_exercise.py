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
    # Claude가 이미 답변을 시작한 것처럼 assistant 메시지를 미리 넣습니다.
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def chat(messages, stop_sequences=None):
    # Claude API에 보낼 기본 요청 값입니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
    }

    # stop sequence를 만나면 그 문자열을 출력에 포함하지 않고 생성을 멈춥니다.
    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    message = client.messages.create(**params)

    return message.content[0].text


def run():
    # 대화 기록을 저장할 리스트입니다.
    messages = []

    prompt = """
Generate three different sample AWS CLI commands.
Each command should be very short.
"""

    add_user_message(messages, prompt)

    # prefill은 코드블록 시작 문자가 아니어도 됩니다.
    # 여기서는 <commands> 태그와 첫 "aws"를 미리 넣어 명령어만 이어 쓰게 만듭니다.
    # assistant prefill은 공백으로 끝나면 안 되므로 "aws "가 아니라 "aws"까지만 넣습니다.
    add_assistant_message(messages, "Here are all three commands in a single block without any comments:```bash")
    
    # Claude가 닫는 태그를 생성하려는 순간 멈춰 태그와 설명을 출력에서 제외합니다.
    text = chat(messages, stop_sequences=["```"])

    # prefill로 넣은 "aws"와 Claude가 이어 쓴 내용을 합쳐야 첫 번째 명령이 완성됩니다.
    # text 앞의 공백은 첫 명령의 "aws s3" 사이 공백일 수 있으므로 지우지 않습니다.
    commands = text.strip()

    print(commands)
