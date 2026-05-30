from anthropic import Anthropic
from anthropic.types import Message
from dotenv import load_dotenv


load_dotenv()

client = Anthropic()
model = "claude-sonnet-4-5-20250929"


# 이 파일에서 가장 중요한 전체 흐름:
#
# 사용자: "다리 근육을 키우는 데 가장 좋은 운동은 뭐야?"
#   ↓
# Python 앱: Claude에게 질문 + web_search schema 전송
#   ↓
# Claude: 최신 정보나 출처가 필요하다고 판단
#   ↓
# Anthropic 서버: 실제 웹 검색 실행
#   ↓
# Claude: 검색 결과를 읽고 인용이 포함된 최종 답변 생성
#   ↓
# Python 앱: 응답 block들을 출력
#
# 핵심:
# web_search는 server tool입니다.
# text editor tool과 달리 우리 Python 코드가 검색을 직접 실행하지 않습니다.
# Anthropic 서버가 검색 실행과 결과 전달까지 처리합니다.
#
# 그래서 이 파일에는 run_tool(), run_tools(), tool_result loop가 필요하지 않습니다.


# ---------------------------------------------------------------------------
# 1. Helper functions
# ---------------------------------------------------------------------------

def add_user_message(messages, message):
    # Claude API는 이전 대화를 자동으로 기억하지 않습니다.
    # user 메시지를 messages 리스트에 직접 추가합니다.
    #
    # Message 객체가 들어오면 안쪽 content만 저장하고,
    # 일반 문자열이 들어오면 문자열 자체를 저장합니다.
    user_message = {
        "role": "user",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(user_message)


def add_assistant_message(messages, message):
    # assistant 응답도 messages에 직접 저장할 수 있게 만든 helper입니다.
    #
    # 이번 예제는 한 번의 API 호출만 하지만,
    # 후속 질문을 이어가려면 response.content 전체를 저장해야 합니다.
    assistant_message = {
        "role": "assistant",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None):
    # Claude에게 메시지를 보내는 공통 helper입니다.
    #
    # 이번 강의에서 중요한 부분:
    # tools=[web_search_schema]를 넘기면 Claude가 웹 검색 도구를 사용할 수 있습니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature,
    }

    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    if tools:
        params["tools"] = tools

    if system:
        params["system"] = system

    message = client.messages.create(**params)
    return message


# ---------------------------------------------------------------------------
# 2. Built-in web search schema
# ---------------------------------------------------------------------------

web_search_schema = {
    # web_search tool은 Anthropic 서버에서 실행됩니다.
    #
    # 일반 사용자 정의 tool:
    # - Python 함수 직접 작성
    # - JSON schema 직접 작성
    # - run_tool()로 실제 함수 실행
    # - tool_result를 Claude에게 다시 전달
    #
    # web_search server tool:
    # - 아래 schema stub만 전달
    # - Anthropic 서버가 실제 검색 실행
    # - Anthropic 서버가 검색 결과를 Claude에게 전달
    # - Claude가 검색 결과를 바탕으로 최종 답변 작성
    "type": "web_search_20250305",
    "name": "web_search",

    # Claude는 첫 검색 결과가 충분하지 않으면 후속 검색을 할 수 있습니다.
    # max_uses는 한 API 요청 안에서 허용할 최대 검색 횟수입니다.
    # 검색이 과도하게 반복되는 것을 막습니다.
    "max_uses": 5,

    # allowed_domains가 있으면 해당 도메인의 결과만 검색에 사용합니다.
    # 운동이나 건강 관련 질문이므로 nih.gov로 제한해서 신뢰도 높은 출처를 사용합니다.
    "allowed_domains": ["nih.gov"],
}


# ---------------------------------------------------------------------------
# 3. Response block 확인
# ---------------------------------------------------------------------------

def print_response_blocks(response):
    # web_search를 사용하면 response.content에는 여러 종류의 block이 들어올 수 있습니다.
    #
    # 대표적인 block:
    #
    # TextBlock
    #   Claude가 작성한 최종 자연어 답변입니다.
    #   citations가 있으면 답변의 특정 문장이 어떤 출처에 근거했는지 확인할 수 있습니다.
    #
    # ServerToolUseBlock
    #   Claude가 Anthropic 서버에 요청한 검색어를 보여줍니다.
    #
    # WebSearchToolResultBlock
    #   Anthropic 서버가 반환한 웹 검색 결과 묶음입니다.
    #
    # WebSearchResultBlock
    #   검색 결과 안에 포함된 개별 페이지 정보입니다.
    #   보통 title, url 같은 정보를 포함합니다.
    for index, block in enumerate(response.content, start=1):
        print(f"Block {index}")
        print(f"- type: {block.type}")

        if block.type == "text":
            print(f"- text: {block.text}")

            # citations는 TextBlock 안에 들어올 수 있습니다.
            # SDK 버전에 따라 citations가 없거나 None일 수 있으므로 getattr()을 사용합니다.
            citations = getattr(block, "citations", None) or []

            for citation_index, citation in enumerate(citations, start=1):
                print(f"- citation {citation_index}:")
                print(f"  - title: {getattr(citation, 'title', None)}")
                print(f"  - url: {getattr(citation, 'url', None)}")
                print(f"  - cited_text: {getattr(citation, 'cited_text', None)}")

        elif block.type == "server_tool_use":
            # Claude가 어떤 검색어를 사용했는지 확인할 수 있습니다.
            print(f"- name: {block.name}")
            print(f"- input: {block.input}")

        elif block.type == "web_search_tool_result":
            # 검색 결과 묶음입니다.
            # content 안에는 개별 검색 결과 block들이 들어올 수 있습니다.
            print("- search results:")

            for result in block.content:
                print(f"  - type: {result.type}")

                if result.type == "web_search_result":
                    print(f"    - title: {result.title}")
                    print(f"    - url: {result.url}")

        print()


# ---------------------------------------------------------------------------
# 4. 실행 예제
# ---------------------------------------------------------------------------

def run():
    # 원본 강의와 동일한 질문입니다.
    #
    # allowed_domains=["nih.gov"]가 있으므로,
    # Claude가 검색을 선택하면 nih.gov 결과만 사용합니다.
    messages = []
    add_user_message(
        messages,
        """
What's the best exercise for gaining leg muscle?
""",
    )

    response = chat(
        messages,
        tools=[web_search_schema],
    )

    add_assistant_message(messages, response)

    print("Claude response:")
    print(response)
    print()

    print("Response blocks:")
    print_response_blocks(response)
