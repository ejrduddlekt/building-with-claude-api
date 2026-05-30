# Section 01. Accessing Claude With the API

## 1. 기본 API 요청

Claude API 요청의 핵심 함수는 `client.messages.create()`이다.

필수 값:

- `model`: 사용할 Claude 모델 이름
- `max_tokens`: 응답 최대 길이 제한
- `messages`: 대화 메시지 목록

기본 구조:

```python
message = client.messages.create(
    model=model,
    max_tokens=1000,
    messages=[
        {"role": "user", "content": "질문 내용"}
    ],
)

print(message.content[0].text)
```

`message.content[0].text`는 Claude 응답에서 실제 텍스트만 꺼내는 코드다.

## 2. 환경 변수와 API 키

API 키는 코드에 직접 쓰지 않고 `.env`에 저장한다.

```env
ANTHROPIC_API_KEY="your-api-key"
```

Python에서는 `load_dotenv()`로 `.env`를 읽는다.

```python
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()
```

`.env`는 반드시 `.gitignore`에 포함해야 한다.

## 3. Messages 구조

Claude API는 대화 기록을 서버에 저장하지 않는다.

즉, 매 요청은 독립적이다. 이전 대화를 이어가려면 직접 `messages` 리스트를 관리해야 한다.

메시지 형태:

```python
{"role": "user", "content": "사용자 입력"}
{"role": "assistant", "content": "Claude 답변"}
```

멀티턴 대화 흐름:

```text
user 메시지 추가
→ Claude 호출
→ assistant 답변 추가
→ 다음 user 메시지 추가
→ 전체 messages를 다시 Claude에게 보냄
```

핵심 helper:

```python
def add_user_message(messages, text):
    messages.append({"role": "user", "content": text})

def add_assistant_message(messages, text):
    messages.append({"role": "assistant", "content": text})
```

## 4. 간단한 챗봇 구조

터미널 챗봇은 `while True`로 계속 입력을 받는다.

```python
messages = []

while True:
    user_input = input("> ")
    add_user_message(messages, user_input)
    answer = chat(messages)
    add_assistant_message(messages, answer)
    print(answer)
```

`chat(messages)` 안에서 `client.messages.create(...)`가 실행된다. 이 호출은 Claude 응답이 올 때까지 기다리는 동기 방식이다.

## 5. System Prompt

`system`은 Claude의 역할, 말투, 응답 방식을 정하는 지시문이다.

예:

```python
system = """
You are a patient math tutor.
Do not directly answer a student's questions.
Guide them step by step.
"""
```

API 호출:

```python
client.messages.create(
    model=model,
    max_tokens=1000,
    system=system,
    messages=messages,
)
```

`system`은 “무엇을 답할지”보다 “어떤 방식으로 답할지”를 제어한다.

선택적 system 처리:

```python
def chat(messages, system=None):
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
    }

    if system:
        params["system"] = system

    return client.messages.create(**params)
```

`**params`는 딕셔너리를 함수 인자로 펼치는 문법이다.

## 6. Temperature

`temperature`는 Claude 응답의 무작위성을 조절한다.

- 낮은 값: 더 일관적, 결정적
- 높은 값: 더 다양함, 창의적

사용 기준:

- `0.0 ~ 0.3`: 데이터 추출, 코드, 사실 기반 응답
- `0.4 ~ 0.7`: 요약, 설명, 일반 작업
- `0.8 ~ 1.0`: 브레인스토밍, 창작, 마케팅 문구

예:

```python
client.messages.create(
    model=model,
    max_tokens=1000,
    messages=messages,
    temperature=0,
)
```

## 7. Response Streaming

일반 요청은 응답이 끝날 때까지 기다린 뒤 한 번에 받는다.

스트리밍은 Claude가 생성하는 텍스트 조각을 바로바로 받을 수 있다.

```python
with client.messages.stream(
    model=model,
    max_tokens=1000,
    messages=messages,
) as stream:
    for text in stream.text_stream:
        print(text, end="")

    final_message = stream.get_final_message()
```

핵심:

- `stream.text_stream`: 실제 텍스트 조각만 순서대로 받음
- `get_final_message()`: 완료된 전체 메시지 객체를 얻음

채팅 앱 UX에서 중요하다. 사용자가 긴 로딩 대신 생성 중인 답변을 바로 볼 수 있다.

## 8. Structured Data

Claude는 기본적으로 설명, 마크다운, 코드블록을 붙이려 한다.

JSON, Python 코드, Regex처럼 “원본만” 필요할 때는 prefill과 stop sequence를 사용한다.

### Assistant Prefill

Claude 답변의 시작 부분을 우리가 미리 넣는 것.

```python
add_assistant_message(messages, "```json")
```

Claude는 이미 JSON 코드블록을 시작했다고 생각하고 이어서 JSON만 작성한다.

### Stop Sequence

특정 문자열을 생성하려는 순간 멈추게 한다.

```python
text = chat(messages, stop_sequences=["```"])
```

흐름:

```text
우리가 미리 넣음: ```json
Claude가 생성함: { ... }
Claude가 닫으려는 순간 멈춤: ```
```

결과적으로 JSON 본문만 얻을 수 있다.

## 9. JSON 파싱

Claude가 생성한 JSON은 처음에는 문자열이다.

```python
clean_json = json.loads(text.strip())
```

- `text.strip()`: 앞뒤 공백, 줄바꿈 제거
- `json.loads(...)`: JSON 문자열을 Python 딕셔너리/리스트로 변환

보기 좋게 다시 출력:

```python
print(json.dumps(clean_json, indent=2))
```

## 10. 시험 포인트

- Claude API는 대화 기록을 저장하지 않는다.
- 멀티턴 대화는 `messages` 리스트를 직접 관리해야 한다.
- `user`와 `assistant` 메시지를 모두 기록해야 맥락이 유지된다.
- `system`은 Claude의 역할과 응답 방식을 정한다.
- `temperature`는 토큰 선택의 무작위성을 조절한다.
- 스트리밍은 UX 개선용이다.
- 구조화된 출력에는 prefill + stop sequence가 유용하다.
- `client.messages.create()`가 실제 API 요청을 보내는 지점이다.
