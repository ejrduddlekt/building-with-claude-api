# Section 03. Prompt Engineering Techniques

## 1. Prompt Engineering의 목적

Prompt engineering은 한 번에 완벽한 프롬프트를 쓰는 기술이 아니다.

기본 흐름은 반복 개선이다.

```text
목표 설정
→ 초기 프롬프트 작성
→ 평가
→ 프롬프트 엔지니어링 기법 적용
→ 다시 평가
→ 만족할 때까지 반복
```

핵심은 감으로 고치는 것이 아니라, 평가 점수를 보면서 개선하는 것이다.

이번 섹션의 예시는 운동선수 1일 식단 계획 프롬프트다.

프롬프트가 받아야 하는 입력:

- `height`: 운동선수 키
- `weight`: 운동선수 몸무게
- `goal`: 운동선수 목표
- `restrictions`: 식단 제한

초기 프롬프트:

```python
def run_prompt(prompt_inputs):
    prompt = f"""
What should this person eat?

- Height: {prompt_inputs["height"]}
- Weight: {prompt_inputs["weight"]}
- Goal: {prompt_inputs["goal"]}
- Dietary restrictions: {prompt_inputs["restrictions"]}
"""

    messages = []
    add_user_message(messages, prompt)
    return chat(messages)
```

이 프롬프트는 일부러 단순하다. 목적은 좋은 답을 바로 얻는 것이 아니라, 개선 전 기준점인 baseline을 만드는 것이다.

평가 결과는 JSON과 HTML report로 저장해서 각 테스트 케이스의 출력, 점수, reasoning을 확인한다.

## 2. Being Clear & Direct

프롬프트의 첫 번째 줄은 가장 중요하다.

Claude는 첫 줄에서 무엇을 해야 하는지 방향을 잡는다. 첫 줄이 모호하면 이후에 정보가 있어도 답변 품질이 흔들릴 수 있다.

### Clear

Clear는 단순하고 모호하지 않은 언어로 정확히 원하는 것을 말하는 것이다.

나쁜 예:

```text
I need to know about those things people put on their roofs that use sun - those solar panel things, I think they're called
```

좋은 예:

```text
Write three paragraphs about how solar panels work.
```

좋은 예에는 세 가지가 있다.

- 동사: `Write`
- 분량: `three paragraphs`
- 주제: `how solar panels work`

### Direct

Direct는 질문이 아니라 지시 형태로 쓰는 것이다.

나쁜 예:

```text
I was reading about renewable energy and geothermal energy sounds neat. What countries use it?
```

좋은 예:

```text
Identify three countries that use geothermal energy. Include generation stats for each.
```

좋은 첫 줄은 보통 직접적인 동사로 시작한다.

- `Write`
- `Create`
- `Generate`
- `Identify`
- `List`
- `Explain`
- `Summarize`

피해야 할 형태:

```text
Can you tell me about X?
What are some ways to do Y?
```

질문형은 Claude가 답변 방향을 스스로 추측하게 만든다. 지시형은 Claude가 해야 할 일을 바로 알게 한다.

## 3. 식단 프롬프트 첫 줄 개선

초기 프롬프트의 첫 줄:

```text
What should this person eat?
```

개선된 첫 줄:

```text
Generate a one-day meal plan for an athlete that meets their dietary restrictions.
```

개선된 첫 줄이 담고 있는 정보:

- 액션: `Generate`
- 산출물: `a meal plan`
- 범위: `one-day`
- 대상: `for an athlete`
- 조건: `meets their dietary restrictions`

점수 변화:

```text
Prompt v1: What should this person eat?
Score: 2.32

Prompt v2: Generate a one-day meal plan for an athlete...
Score: 3.92

Improvement: +1.60
```

첫 줄만 바꿔도 점수가 오른다. 가장 간단하면서 효과가 큰 기법이다.

좋은 첫 줄 공식:

```text
동사 + 산출물 + 범위/조건
```

## 4. Being Specific

Being specific은 Claude가 따라야 할 기준을 구체적으로 주는 것이다.

지시만 있고 기준이 없으면 Claude는 길이, 형식, 포함 요소를 스스로 결정한다. 그래서 답변이 매번 달라지고 평가 점수도 불안정해진다.

예:

```text
Write a short story about a character who discovers a hidden talent.
```

이 프롬프트는 `short`가 얼마나 짧은지, 어떤 구조가 필요한지, 어떤 스타일이어야 하는지 명확하지 않다.

구체성을 높이는 방법은 크게 두 가지다.

### 출력 품질 가이드라인

출력이 갖춰야 할 속성을 직접 나열한다.

예:

- 길이
- 형식
- 포함해야 할 요소
- 어조
- 스타일
- 제한 조건

식단 프롬프트에 추가한 가이드라인:

```text
Guidelines:
1. Include accurate daily calorie amount
2. Show protein, fat, and carb amounts
3. Specify when to eat each meal
4. Use only foods that fit restrictions
5. List all portion sizes in grams
6. Keep budget-friendly if mentioned
```

점수 변화:

```text
Prompt v2: 첫 줄만 개선
Score: 3.92

Prompt v3: 가이드라인 추가
Score: 7.86

Improvement: +3.94
```

출력 품질 가이드라인은 거의 모든 프롬프트에 유용하다. Claude에게 “좋은 답변의 조건”을 명시하기 때문이다.

### 프로세스 단계

복잡한 문제에서는 Claude가 따라야 할 사고 순서를 지정할 수 있다.

예:

```text
Write a one-page decision report to troubleshoot
why a sales team's numbers have dropped 30% last quarter.

Follow these steps:
1. Compare current vs previous market metrics
2. Identify relevant industry changes
3. Analyze individual team member performance
4. Consider recent organizational changes
5. Review customer feedback
```

프로세스 단계는 Claude가 자연스럽게 놓칠 수 있는 관점을 강제로 검토하게 만든다.

사용 기준:

- 출력 품질 가이드라인: 거의 모든 프롬프트
- 프로세스 단계: 복잡한 분석, 의사결정, 문제 해결
- 둘의 조합: 전문적인 고품질 프롬프트

## 5. XML Tags

XML 태그는 프롬프트 안에서 섹션의 경계를 명확히 나누는 도구다.

형태:

```text
<tag_name>
내용
</tag_name>
```

공식 XML 표준을 엄격하게 지킬 필요는 없다. 중요한 것은 태그명이 내용을 잘 설명하는 것이다.

### 왜 필요한가

프롬프트에 대용량 데이터, 코드, 문서, 여러 변수가 섞이면 Claude가 어디까지가 지시사항이고 어디부터가 참고 데이터인지 헷갈릴 수 있다.

태그 없는 예:

```text
Here are the last 20 pages of our sales records:
{sales_records}

Follow these steps:
1. Compare market metrics...
```

태그 적용 예:

```text
Here are the last 20 pages of our sales records:

<sales_records>
{sales_records}
</sales_records>

Follow these steps:
1. Compare market metrics...
```

### 코드와 문서를 함께 넣는 경우

태그 없는 예:

```text
Debug my code below using the provided documentation.

from datavortex import Pipeline
def process_data(input, output):
    pipeline = Pipeline()

# Creating a data source
csv = DataSource.from_csv("data")
```

태그 적용 예:

```text
Debug my code below using the provided documentation.

<my_code>
from datavortex import Pipeline
def process_data(input, output):
    pipeline = Pipeline()
</my_code>

<docs>
# Creating a data source
csv = DataSource.from_csv("data")
</docs>
```

Claude는 `<my_code>`와 `<docs>`를 보고 코드와 문서의 역할을 분리해서 이해한다.

### 식단 프롬프트 적용

```python
prompt = f"""
Generate a meal plan based on the athlete information below.

<athlete_information>
- Height: {prompt_inputs["height"]}
- Weight: {prompt_inputs["weight"]}
- Goal: {prompt_inputs["goal"]}
- Restrictions: {prompt_inputs["restrictions"]}
</athlete_information>
"""
```

`<athlete_information>`으로 묶으면 네 개의 값이 모두 같은 운동선수의 정보라는 점이 분명해진다.

좋은 태그명:

```text
<sales_records>
<athlete_information>
<my_code>
<docs>
<sample_input>
<ideal_output>
```

나쁜 태그명:

```text
<data>
<info>
<content>
```

태그명이 구체적일수록 Claude가 각 섹션의 목적을 더 잘 이해한다.

XML 태그가 특히 유용한 상황:

- 대용량 데이터나 컨텍스트를 넣을 때
- 코드, 문서, 데이터가 섞일 때
- 여러 변수를 프롬프트에 보간할 때
- Claude가 내용 간 관계를 정확히 알아야 할 때

짧고 단순한 프롬프트에서는 효과가 작을 수 있다. 프롬프트가 복잡해질수록 가치가 커진다.

## 6. Providing Examples

예시는 말로 설명하기 어려운 요구사항을 직접 보여주는 방법이다.

Claude에게 “이런 식으로 답해”를 보여주면, 미묘한 형식이나 스타일, 코너 케이스를 더 잘 따라간다.

### One-Shot과 Multi-Shot

One-Shot:

```text
예시 1개 제공
```

사용 상황:

- 단순한 패턴 전달
- 출력 형식이 크게 복잡하지 않을 때

Multi-Shot:

```text
예시 여러 개 제공
```

사용 상황:

- 코너 케이스가 많을 때
- 입력 유형이 다양할 때
- 미묘한 판단 기준이 필요할 때

### 풍자 감정 분석 예시

기본 프롬프트:

```text
Categorize the sentiment of the below tweet:

<input_tweet>
{tweet}
</input_tweet>

If positive, respond with "Positive".
If negative, respond with "Negative".
```

풍자 예시 추가:

```text
Here is an example input with an ideal response:

<sample_input>
Great game tonight!
</sample_input>

<ideal_output>
Positive
</ideal_output>

Be especially careful with tweets that contain sarcasm.

<sample_input>
Oh yeah, I really needed a flight delay tonight! Excellent!
</sample_input>

<ideal_output>
Negative
</ideal_output>
```

표면적으로는 긍정 단어가 있어도 실제 감정은 부정일 수 있다. 이런 코너 케이스는 설명보다 예시가 더 효과적이다.

### 식단 프롬프트 예시

평가에서 높은 점수를 받은 출력을 예시로 재활용할 수 있다.

```text
Here is an example of an ideal meal plan:

<sample_input>
height: 170cm
weight: 70kg
goal: maintain fitness
restrictions: high cholesterol
</sample_input>

<ideal_output>
Calorie Target: approximately 2500 calories
Macronutrient Breakdown: Protein 140g, Fat 70g, Carbs 340g

Breakfast (7:00 AM): Oatmeal 80g, berries 100g, walnuts 15g...
Lunch (1:00 PM): Grilled chicken breast 120g, mixed greens 150g...
Dinner (7:00 PM): Baked salmon 140g, broccoli 200g, quinoa 75g...
</ideal_output>

This output is good because it includes calories, macros, timing,
exact foods, portions, and respects the athlete's restrictions.
```

예시를 줄 때는 왜 좋은 출력인지 이유도 함께 적으면 좋다. Claude가 형식뿐 아니라 품질 기준까지 이해하기 때문이다.

예시가 특히 유용한 상황:

- 코너 케이스 처리
- 복잡한 출력 형식 정의
- 원하는 어조나 스타일 시연
- 모호한 입력을 어떻게 처리할지 보여줄 때
- 평가에서 최고점 받은 출력을 재사용할 때

## 7. Prompt Engineering 기법 적용 순서

식단 프롬프트 개선 흐름:

```text
v1. 초기 프롬프트
What should this person eat?
Score: 2.32

v2. Clear & Direct
Generate a one-day meal plan for an athlete...
Score: 3.92

v3. Being Specific
Guidelines 6개 추가
Score: 7.86

v4. XML Tags
<athlete_information>으로 입력 구조화

v5. Providing Examples
<sample_input>, <ideal_output> 예시 추가
```

중요한 점:

한 번에 모든 기법을 넣는 것보다, 하나씩 적용하고 평가하는 것이 좋다. 그래야 어떤 변경이 점수를 올렸는지 알 수 있다.

## 8. 시험 포인트

- Prompt engineering은 반복 개선 과정이다.
- 평가 없이 프롬프트를 고치면 어떤 변경이 효과 있었는지 알기 어렵다.
- 첫 줄은 Claude가 작업 방향을 잡는 가장 중요한 부분이다.
- 좋은 첫 줄은 `동사 + 산출물 + 범위/조건` 형태가 좋다.
- 질문형보다 지시형이 좋다.
- Being Specific은 Claude가 따라야 할 기준을 구체적으로 주는 것이다.
- 출력 품질 가이드라인은 거의 모든 프롬프트에 유용하다.
- 프로세스 단계는 복잡한 분석이나 의사결정에 유용하다.
- XML 태그는 프롬프트 안의 섹션 경계를 명확히 나눈다.
- 태그명은 `<data>`보다 `<sales_records>`처럼 구체적인 것이 좋다.
- 예시는 설명보다 강하다.
- One-Shot은 예시 1개, Multi-Shot은 예시 여러 개다.
- 예시는 `<sample_input>`, `<ideal_output>`처럼 XML 태그와 함께 쓰면 좋다.
- 평가에서 높은 점수를 받은 출력을 예시로 재활용할 수 있다.
- 가장 좋은 방식은 기법을 하나씩 적용하고 점수 변화를 확인하는 것이다.
