from datetime import datetime

from anthropic import Anthropic
from anthropic.types import ToolParam
from dotenv import load_dotenv


load_dotenv()

client = Anthropic()
model = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# 1. 메시지 helper
# ---------------------------------------------------------------------------

def add_user_message(messages, text):
    # 일반 user 메시지는 지금까지와 동일하게 문자열 content를 넣습니다.
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, content):
    # Tool use 응답에서는 assistant content가 단순 문자열이 아닐 수 있습니다.
    #
    # response.content는 보통 이런 block list입니다.
    # [
    #   TextBlock(...),
    #   ToolUseBlock(...)
    # ]
    #
    # Claude는 대화 기록을 서버에 저장하지 않기 때문에,
    # 이 block list 전체를 그대로 messages에 다시 넣어야 다음 요청에서 맥락이 이어집니다.
    assistant_message = {"role": "assistant", "content": content}
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None):
    # 기본 API 호출 helper입니다.
    #
    # 이번 강의에서 새로 추가된 부분은 tools입니다.
    # tools에 schema 목록을 넣으면 Claude가 사용할 수 있는 도구를 알게 됩니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature,
    }

    if system:
        params["system"] = system

    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    if tools:
        params["tools"] = tools

    message = client.messages.create(**params)
    return message


# ---------------------------------------------------------------------------
# 2. 실제 Python tool function
# ---------------------------------------------------------------------------

def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
    # Claude가 직접 시간을 알 수 없을 때 호출하게 만들 함수입니다.
    #
    # 중요한 점:
    # Claude가 이 함수를 직접 실행하는 것이 아닙니다.
    # Claude는 "이 함수가 필요하다"고 tool_use block으로 알려주고,
    # 실제 실행은 우리 Python 코드가 합니다.
    if not date_format:
        # 에러 메시지는 Claude가 읽고 다시 시도할 수 있으므로 명확하게 작성합니다.
        raise ValueError("date_format cannot be empty")

    return datetime.now().strftime(date_format)


# ---------------------------------------------------------------------------
# 3. Claude에게 tool function을 설명하는 JSON schema
# ---------------------------------------------------------------------------

get_current_datetime_schema = ToolParam({
    # name은 실제 Python 함수 이름과 맞춰두면 관리하기 쉽습니다.
    "name": "get_current_datetime",
    # description은 Claude가 "언제 이 도구를 써야 하는지" 판단하는 데 사용합니다.
    "description": (
        "Returns the current date and time formatted according to the specified "
        "format. Use this when the user asks for the current date, current time, "
        "or a timestamp in a specific format."
    ),
    # input_schema는 함수가 받을 수 있는 인자 목록과 타입을 설명합니다.
    "input_schema": {
        "type": "object",
        "properties": {
            "date_format": {
                "type": "string",
                "description": (
                    "A string specifying the format of the returned datetime. "
                    "Uses Python's strftime format codes. For example, "
                    "'%H:%M:%S' returns the exact time."
                ),
                "default": "%Y-%m-%d %H:%M:%S",
            }
        },
        "required": [],
    },
})


# ---------------------------------------------------------------------------
# 4. Tool-enabled API 호출 흐름
# ---------------------------------------------------------------------------

def run():
    # 전체 흐름:
    #
    # 1. 사용자 메시지를 만든다.
    # 2. Claude API 호출에 tools=[schema]를 함께 보낸다.
    # 3. Claude가 필요하다고 판단하면 tool_use block을 응답한다.
    # 4. assistant 메시지는 response.content 전체를 대화 기록에 저장한다.
    # 5. 이번 강의에서는 block 구조를 출력해서 확인한다.
    #
    # 다음 강의에서는 tool_use block을 읽어서 실제 Python 함수를 실행하고,
    # 그 결과를 다시 Claude에게 보내는 단계로 이어집니다.
    messages = []
    add_user_message(messages, "What is the exact time, formatted as HH:MM:SS?")

    # tools 파라미터에 schema를 넣으면 Claude가 get_current_datetime 도구를 알게 됩니다.
    # 이 호출은 아직 Python 함수를 실행하지 않습니다.
    # Claude가 "이 도구를 호출해줘"라고 요청할 수 있게 만드는 단계입니다.
    response = chat(
        messages,
        tools=[get_current_datetime_schema],
    )

    # 중요:
    # tool_use 응답은 text만 저장하면 안 됩니다.
    # response.content 전체를 저장해야 tool_use block까지 대화 기록에 남습니다.
    add_assistant_message(messages, response.content)

    # response.content는 여러 block으로 구성될 수 있습니다.
    # 예:
    # - text block: Claude가 사용자에게 설명하는 자연어
    # - tool_use block: 우리 코드가 실행해야 할 함수 이름과 인자
    print("Claude response content blocks:")
    print(response.content)
    print()

    for block in response.content:
        print(f"type: {block.type}")

        if block.type == "text":
            # Claude가 사용자에게 말한 일반 텍스트입니다.
            print(f"text: {block.text}")

        if block.type == "tool_use":
            # Claude가 요청한 tool call 정보입니다.
            #
            # id: 나중에 tool result를 돌려줄 때 어떤 호출의 결과인지 연결하는 값
            # name: 호출해야 할 Python 함수 이름
            # input: 함수에 넘길 인자 딕셔너리
            print(f"id: {block.id}")
            print(f"name: {block.name}")
            print(f"input: {block.input}")

        print()
