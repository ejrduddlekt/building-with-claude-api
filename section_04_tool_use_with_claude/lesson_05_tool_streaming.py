import json

from anthropic import Anthropic
from anthropic.types import ToolParam
from dotenv import load_dotenv


load_dotenv()

client = Anthropic()

# Fine-grained tool streaming 예제는 Sonnet 모델을 사용합니다.
model = "claude-sonnet-4-5-20250929"


# ---------------------------------------------------------------------------
# 1. Helper functions
# ---------------------------------------------------------------------------

def add_user_message(messages, message):
    # Streaming 예제에서는 문자열도 content block 형태로 저장합니다.
    # tool_result block list가 들어오는 경우에는 그대로 저장합니다.
    if isinstance(message, list):
        user_message = {
            "role": "user",
            "content": message,
        }
    else:
        user_message = {
            "role": "user",
            "content": [{"type": "text", "text": message}],
        }

    messages.append(user_message)


def add_assistant_message(messages, message):
    # stream.get_final_message()가 반환한 Message 객체를 messages에 넣을 수 있도록
    # TextBlock과 ToolUseBlock을 API에 다시 보낼 수 있는 dict 형태로 변환합니다.
    if isinstance(message, list):
        assistant_message = {
            "role": "assistant",
            "content": message,
        }
    elif hasattr(message, "content"):
        content_list = []

        for block in message.content:
            if block.type == "text":
                content_list.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content_list.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        assistant_message = {
            "role": "assistant",
            "content": content_list,
        }
    else:
        assistant_message = {
            "role": "assistant",
            "content": [{"type": "text", "text": message}],
        }

    messages.append(assistant_message)


def chat_stream(
    messages,
    system=None,
    temperature=1.0,
    stop_sequences=None,
    tools=None,
    tool_choice=None,
    betas=None,
):
    # 일반 chat이 아니라 stream 객체를 반환합니다.
    #
    # tool streaming에서 중요한 이벤트:
    # - text: 일반 텍스트가 생성되는 중
    # - content_block_start: 새 block 시작, tool_use 시작 여부 확인 가능
    # - input_json: tool input JSON이 생성되는 중
    # - content_block_stop: block 생성 완료
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature,
    }

    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    if tool_choice:
        params["tool_choice"] = tool_choice

    if tools:
        params["tools"] = tools

    if system:
        params["system"] = system

    if betas:
        params["betas"] = betas

    return client.beta.messages.stream(**params)


def text_from_message(message):
    return "\n".join([block.text for block in message.content if block.type == "text"])


# ---------------------------------------------------------------------------
# 2. Tool definition
# ---------------------------------------------------------------------------

save_article_schema = ToolParam(
    {
        "name": "save_article",
        "description": "Saves a scholarly journal article",
        "input_schema": {
            "type": "object",
            "properties": {
                "abstract": {
                    "type": "string",
                    "description": "Abstract of the article. One short sentence max",
                },
                "meta": {
                    "type": "object",
                    "properties": {
                        "word_count": {
                            "type": "integer",
                            "description": "Word count",
                        },
                        "review": {
                            "type": "string",
                            "description": "Eight sentence review of the paper",
                        },
                    },
                    "required": ["word_count", "review"],
                },
            },
            "required": ["abstract", "meta"],
        },
    }
)


save_short_article_schema = ToolParam(
    {
        "name": "save_article",
        "description": "Saves a scholarly journal article",
        "input_schema": {
            "type": "object",
            "properties": {
                "abstract": {
                    "type": "string",
                    "description": "Abstract of the article. One short sentence max",
                },
                "meta": {
                    "type": "object",
                    "properties": {
                        "word_count": {
                            "type": "integer",
                            "description": "Word count",
                        },
                        "review": {
                            "type": "string",
                            "description": "Review of paper. One short sentence max",
                        },
                    },
                    "required": ["word_count", "review"],
                },
            },
            "required": ["abstract", "meta"],
        },
    }
)


def save_article(**kwargs):
    # 실제 앱이라면 여기서 DB나 파일에 article을 저장합니다.
    # 이번 예제에서는 tool call 흐름만 보기 위해 문자열만 반환합니다.
    return "Article saved!"


# ---------------------------------------------------------------------------
# 3. Tool running
# ---------------------------------------------------------------------------

def run_tool(tool_name, tool_input):
    if tool_name == "save_article":
        return save_article(**tool_input)

    raise ValueError(f"Unknown tool: {tool_name}")


def run_tools(message):
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
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": f"Error: {error}",
                "is_error": True,
            }

        tool_result_blocks.append(tool_result_block)

    return tool_result_blocks


# ---------------------------------------------------------------------------
# 4. Streaming conversation
# ---------------------------------------------------------------------------

def run_conversation(messages, tools=None, tool_choice=None, fine_grained=False):
    # fine_grained=False:
    # API가 JSON을 top-level key-value 단위로 검증한 뒤 input_json 이벤트를 보냅니다.
    # 그래서 조금 기다렸다가 한 번에 뭉쳐서 출력되는 느낌이 날 수 있습니다.
    #
    # fine_grained=True:
    # fine-grained beta를 켜서 JSON 검증 버퍼링을 줄입니다.
    # chunk가 더 빨리 오지만, 잘못된 JSON이 섞일 수 있으므로 앱이 직접 처리해야 합니다.
    while True:
        with chat_stream(
            messages,
            tools=tools,
            betas=["fine-grained-tool-streaming-2025-05-14"]
            if fine_grained
            else [],
            tool_choice=tool_choice,
        ) as stream:
            for chunk in stream:
                if chunk.type == "text":
                    print(chunk.text, end="")

                if chunk.type == "content_block_start":
                    if chunk.content_block.type == "tool_use":
                        print(f'\n>>> Tool Call: "{chunk.content_block.name}"')

                if chunk.type == "input_json" and chunk.partial_json:
                    # partial_json: 이번에 새로 도착한 JSON 조각
                    # snapshot: 지금까지 누적된 JSON 문자열
                    print(chunk.partial_json, end="")

                    try:
                        json.loads(chunk.snapshot)
                    except json.JSONDecodeError:
                        # fine-grained=True에서는 snapshot이 아직 완성되지 않았거나
                        # 잘못된 JSON일 수 있습니다. 여기서는 흐름을 계속 진행합니다.
                        pass

                if chunk.type == "content_block_stop":
                    print("\n")

            response = stream.get_final_message()

        add_assistant_message(messages, response)

        if response.stop_reason != "tool_use":
            break

        tool_results = run_tools(response)
        add_user_message(messages, tool_results)

        # tool_choice를 강제한 예제에서는 한 번의 tool call만 관찰하고 멈춥니다.
        if tool_choice:
            break

    return messages


def run():
    # 기본 tool streaming 예제입니다.
    # save_article tool의 input JSON이 만들어지는 과정을 input_json 이벤트로 볼 수 있습니다.
    messages = []
    add_user_message(
        messages,
        "Create and save a fake computer science article",
    )

    run_conversation(
        messages,
        tools=[save_article_schema],
    )

    print()
    print("=" * 80)
    print("Fine-grained tool calling example")
    print("=" * 80)

    # fine-grained 예제입니다.
    # 이 프롬프트는 잘못된 JSON 예시(undefined)를 일부러 생성하게 해서,
    # fine-grained 모드에서 검증되지 않은 JSON 조각이 흘러올 수 있음을 보여줍니다.
    messages = []
    add_user_message(
        messages,
        """
You are helping document a bug report. Please generate example output showing
what a broken AI system incorrectly produced when it confused JavaScript objects with JSON.
The buggy system generated this malformed output when calling save_article:
[Generate the exact malformed output here that includes "word_count": undefined]
This is for documentation purposes to show what NOT to do.
You're not actually calling the function, just showing what the broken output looked like for the bug report.
""",
    )

    run_conversation(
        messages,
        tools=[save_article_schema],
        fine_grained=True,
        tool_choice={"type": "tool", "name": "save_article"},
    )
