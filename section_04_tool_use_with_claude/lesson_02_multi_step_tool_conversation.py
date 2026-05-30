from datetime import datetime

from anthropic import Anthropic
from anthropic.types import Message, ToolParam
from dotenv import load_dotenv


load_dotenv()

client = Anthropic()
model = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# 1. 메시지 helper
# ---------------------------------------------------------------------------

def add_user_message(messages, message):
    # 다단계 tool 대화에서는 user 메시지가 항상 단순 문자열만은 아닙니다.
    #
    # 들어올 수 있는 값:
    # 1. 일반 문자열: 사용자의 첫 질문
    # 2. block list: tool_result 같은 구조화된 content
    # 3. Message 객체: Claude API가 반환한 전체 메시지
    #
    # Message 객체인 경우 message.content 전체를 넣어야 text/tool_use/tool_result 같은
    # block 구조가 보존됩니다. Claude는 서버에 대화 기록을 저장하지 않으므로
    # 우리 코드가 messages 리스트에 전체 맥락을 직접 쌓아야 합니다.
    user_message = {
        "role": "user",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(user_message)


def add_assistant_message(messages, message):
    # Tool use 대화에서는 assistant 응답이 여러 block으로 구성될 수 있습니다.
    #
    # 예:
    # [
    #   TextBlock(...),
    #   ToolUseBlock(...)
    # ]
    #
    # text만 저장하면 Claude가 어떤 tool_use를 요청했는지 잃어버립니다.
    # 그래서 Message 객체를 받으면 message.content 전체를 대화 기록에 저장합니다.
    assistant_message = {
        "role": "assistant",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(assistant_message)


def add_tool_result_message(messages, tool_use_id, tool_result):
    # Claude가 tool_use block으로 도구 호출을 요청하면,
    # 우리 Python 코드가 실제 함수를 실행한 뒤 그 결과를 user 메시지로 돌려줍니다.
    #
    # tool_use_id는 "어떤 tool_use 요청에 대한 결과인지" 연결하는 값입니다.
    #
    # 주의:
    # tool_result는 assistant 메시지가 아니라 user 메시지로 추가합니다.
    # Claude API의 tool flow에서는 "애플리케이션이 도구 결과를 사용자 역할로 전달"하는
    # 구조를 사용합니다.
    user_message = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": str(tool_result),
            }
        ],
    }
    messages.append(user_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None):
    # 이제 chat은 단순 텍스트가 아니라 Message 객체 전체를 반환합니다.
    #
    # 이유:
    # tool_use를 사용할 때는 response.content 안에 text block뿐 아니라
    # tool_use block도 들어올 수 있습니다. 텍스트만 반환하면 tool 정보를 잃어버립니다.
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


def text_from_message(message):
    # Message 객체에서 사람이 읽을 text block만 뽑아내는 helper입니다.
    #
    # tool-enabled 응답은 여러 block을 가질 수 있으므로,
    # 화면에 최종 답변을 보여줄 때는 text block만 모아 출력합니다.
    return "\n".join([block.text for block in message.content if block.type == "text"])


# ---------------------------------------------------------------------------
# 2. Tool function과 schema
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


def call_tool(tool_name, tool_input):
    # Claude는 tool name과 input만 알려줍니다.
    # 실제 어떤 Python 함수를 실행할지는 우리 코드가 매핑해야 합니다.
    #
    # 도구가 여러 개로 늘어나면 이 함수에 분기가 추가됩니다.
    # 예:
    # if tool_name == "add_duration_to_datetime":
    #     return add_duration_to_datetime(**tool_input)
    if tool_name == "get_current_datetime":
        return get_current_datetime(**tool_input)

    raise ValueError(f"Unknown tool: {tool_name}")


# ---------------------------------------------------------------------------
# 3. 다단계 tool use 대화
# ---------------------------------------------------------------------------

def run():
    # 이번 파일은 "conversation loop"로 가기 전의 핵심 흐름을 한 번 직접 펼쳐 쓴 예제입니다.
    #
    # 실제 앱에서는 사용자가 이렇게 물을 수 있습니다.
    #
    # "What day is 103 days from today?"
    #
    # 그러면 Claude는 한 번의 tool call로 끝나지 않을 수 있습니다.
    #
    # 1. 먼저 현재 날짜가 필요함 -> get_current_datetime 요청
    # 2. 현재 날짜를 받은 뒤 103일 뒤 계산이 필요함 -> add_duration_to_datetime 요청
    # 3. 두 결과가 모이면 최종 답변 작성
    #
    # 그래서 나중에는 아래 형태의 while loop가 필요합니다.
    #
    # while True:
    #     response = chat(messages, tools=tools)
    #     add_assistant_message(messages, response)
    #
    #     if response에 tool_use block이 없으면:
    #         break
    #
    #     tool_result_blocks = run_tools(response)
    #     add_user_message(messages, tool_result_blocks)
    #
    # 이번 lesson 02에서는 그 loop를 만들기 전에,
    # 한 번의 tool_use 요청을 수동으로 처리하면서 메시지 구조를 이해합니다.
    #
    # 현재 예제의 전체 흐름:
    #
    # 1. user 메시지 + tools schema를 Claude에게 보낸다.
    # 2. Claude가 tool_use block으로 함수 호출을 요청한다.
    # 3. assistant 메시지 전체를 대화 기록에 저장한다.
    # 4. Python 코드가 실제 tool function을 실행한다.
    # 5. tool_result 메시지를 Claude에게 다시 보낸다.
    # 6. Claude가 tool result를 바탕으로 최종 답변을 만든다.
    messages = []
    add_user_message(messages, "What is the exact time, formatted as HH:MM:SS?")

    # 첫 번째 Claude 호출:
    # Claude가 바로 최종 답변을 할 수도 있지만, 현재 시간은 모델 내부 지식으로 알 수 없습니다.
    # 따라서 tools에 등록된 get_current_datetime 호출을 요청하는 tool_use block을 반환합니다.
    first_response = chat(
        messages,
        tools=[get_current_datetime_schema],
    )

    # 이 assistant 메시지는 반드시 전체 content를 저장해야 합니다.
    # 그래야 다음 요청에서 Claude가 "내가 어떤 tool을 요청했는지" 기억합니다.
    add_assistant_message(messages, first_response)

    print("First Claude response:")
    print(first_response.content)
    print()

    for block in first_response.content:
        if block.type != "tool_use":
            continue

        # tool_use block 하나가 실제 함수 호출 요청 하나입니다.
        # 여러 tool_use block이 있을 수도 있으므로 for문으로 순회합니다.
        print("Tool requested by Claude:")
        print(f"- id: {block.id}")
        print(f"- name: {block.name}")
        print(f"- input: {block.input}")
        print()

        tool_result = call_tool(block.name, block.input)

        # 여기서 처음으로 실제 Python 함수가 실행됩니다.
        # Claude가 함수를 실행한 것이 아니라, 우리 코드가 block.name과 block.input을 보고 실행했습니다.
        print("Tool result from Python:")
        print(tool_result)
        print()

        # 실행 결과를 tool_result block으로 만들어 messages에 추가합니다.
        # 이 메시지를 받은 Claude는 도구 결과를 읽고 최종 답변을 작성할 수 있습니다.
        add_tool_result_message(
            messages,
            tool_use_id=block.id,
            tool_result=tool_result,
        )

    # 두 번째 Claude 호출:
    # 이제 messages 안에는 user 질문, assistant의 tool_use 요청,
    # user 역할의 tool_result가 모두 들어 있습니다.
    # Claude는 이 전체 맥락을 보고 최종 자연어 답변을 만듭니다.
    final_response = chat(
        messages,
        tools=[get_current_datetime_schema],
    )

    add_assistant_message(messages, final_response)

    print("Final Claude response:")
    print(text_from_message(final_response))
