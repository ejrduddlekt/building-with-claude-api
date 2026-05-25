# .env 파일을 읽기 위한 함수입니다.
from dotenv import load_dotenv

# Claude API 클라이언트입니다.
from anthropic import Anthropic


# main.py에서 호출할 실행 함수입니다.
def run():
    # .env의 ANTHROPIC_API_KEY를 환경 변수로 불러옵니다.
    load_dotenv()

    # Claude API 클라이언트를 생성합니다.
    client = Anthropic()

    # 사용할 Claude 모델입니다.
    model = "claude-sonnet-4-6"

    # Claude에게 메시지를 보내고 응답을 받습니다.
    message = client.messages.create(
        model=model,
        # 응답 최대 길이 제한입니다.
        max_tokens=1000,
        # Claude에게 전달할 대화 메시지입니다.
        messages=[
            {
                "role": "user",
                "content": "What is quantum computing? Answer in one sentence",
            }
        ],
    )

    # 응답 객체에서 텍스트만 꺼내 출력합니다.
    print(message.content[0].text)
