import json
from datetime import datetime

from anthropic import Anthropic
from anthropic.types import Message, ToolParam
from dotenv import load_dotenv


load_dotenv()

client = Anthropic()
model = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# 1. Helper functions
# ---------------------------------------------------------------------------

def add_user_message(messages, message):
    # message는 문자열, block list, Message 객체일 수 있습니다.
    # Message 객체라면 content 전체를 저장해서 text/tool_use/tool_result block을 보존합니다.
    user_message = {
        "role": "user",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(user_message)


def add_assistant_message(messages, message):
    # assistant 응답도 Message 객체 전체를 받을 수 있게 합니다.
    # tool_use block이 사라지면 다음 턴에서 Claude가 맥락을 잃습니다.
    assistant_message = {
        "role": "assistant",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None):
    # tool loop에서는 text만 필요한 것이 아니라 stop_reason과 content block 전체가 필요합니다.
    # 그래서 message.content[0].text가 아니라 Message 객체 전체를 반환합니다.
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


def text_from_message(message):
    # 화면에 보여줄 때는 text block만 모아 출력합니다.
    return "\n".join([block.text for block in message.content if block.type == "text"])


# ---------------------------------------------------------------------------
# 2. Tool function and schema
# ---------------------------------------------------------------------------

def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
    if not date_format:
        raise ValueError("date_format cannot be empty")

    return datetime.now().strftime(date_format)


get_current_datetime_schema = ToolParam(
    {
        "name": "get_current_datetime",
        "description": (
            "Returns the current date and time formatted according to the specified "
            "format string. This tool provides the current system time formatted as "
            "a string. Use this tool when you need to know the current date and time, "
            "such as for timestamping records, calculating time differences, or "
            "displaying the current time to users."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_format": {
                    "type": "string",
                    "description": (
                        "A string specifying the format of the returned datetime. "
                        "Uses Python's strftime format codes. For example, "
                        "'%Y-%m-%d' returns just the date in YYYY-MM-DD format, "
                        "'%H:%M:%S' returns just the time in HH:MM:SS format, "
                        "'%B %d, %Y' returns a date like 'May 07, 2025'. "
                        "The default is '%Y-%m-%d %H:%M:%S'."
                    ),
                    "default": "%Y-%m-%d %H:%M:%S",
                }
            },
            "required": [],
        },
    }
)


# ---------------------------------------------------------------------------
# 3. Tool runner
# ---------------------------------------------------------------------------

def run_tool(tool_name, tool_input):
    # tool name을 실제 Python 함수로 연결합니다.
    # 도구가 늘어나면 이 함수에 elif 분기를 추가합니다.
    if tool_name == "get_current_datetime":
        return get_current_datetime(**tool_input)

    raise ValueError(f"Unknown tool: {tool_name}")


def run_tools(message):
    # Claude 응답 안에서 tool_use block만 찾아 실행합니다.
    # 한 응답 안에 tool_use block이 여러 개 있을 수 있으므로 list로 처리합니다.
    tool_requests = [block for block in message.content if block.type == "tool_use"]
    tool_result_blocks = []

    for tool_request in tool_requests:
        try:
            tool_output = run_tool(tool_request.name, tool_request.input)
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": json.dumps(tool_output),
                "is_error": False,
            }
        except Exception as error:
            # tool 실행 중 에러가 나도 Claude에게 tool_result block을 돌려줘야 합니다.
            # is_error=True로 보내면 Claude가 에러를 보고 다른 방식으로 다시 시도할 수 있습니다.
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": f"Error: {error}",
                "is_error": True,
            }

        tool_result_blocks.append(tool_result_block)

    return tool_result_blocks


# ---------------------------------------------------------------------------
# 4. Conversation loop
# ---------------------------------------------------------------------------

def run_conversation(messages):
    # Claude가 tool을 더 이상 요청하지 않을 때까지 반복합니다.
    #
    # 핵심 조건:
    # response.stop_reason == "tool_use"이면 아직 도구 실행이 필요합니다.
    # response.stop_reason != "tool_use"이면 최종 답변이 준비된 상태입니다.
    while True:
        response = chat(messages, tools=[get_current_datetime_schema])

        add_assistant_message(messages, response)
        print(text_from_message(response))

        if response.stop_reason != "tool_use":
            break

        tool_results = run_tools(response)
        add_user_message(messages, tool_results)

    return messages


def run():
    # 이 질문은 Claude가 같은 도구를 여러 번 호출해야 할 수 있는 예시입니다.
    #
    # 예:
    # 1. HH:MM 형식 시간이 필요함 -> get_current_datetime("%H:%M")
    # 2. SS 형식 초가 필요함 -> get_current_datetime("%S")
    # 3. 두 결과를 모아 최종 답변
    messages = []
    add_user_message(
        messages,
        "What is the current time in HH:MM format? Also, what is the current time in SS format?",
    )

    final_messages = run_conversation(messages)

    print()
    print("Full conversation history:")
    print(final_messages)
