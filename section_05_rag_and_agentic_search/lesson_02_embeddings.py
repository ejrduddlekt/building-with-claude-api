import re
from pathlib import Path

from dotenv import load_dotenv

try:
    import voyageai
except ImportError as error:
    raise ImportError(
        "voyageai package is not installed. Run: pip install voyageai"
    ) from error


# ---------------------------------------------------------------------------
# Text Embeddings
# ---------------------------------------------------------------------------
#
# lesson 01에서는 긴 문서를 여러 chunk로 나눴습니다.
#
# 이번 lesson 02에서는 각 chunk를 embedding으로 바꿉니다.
#
# 전체 흐름:
#
# report.md 문서
#   ↓
# chunk_by_section()으로 문서를 여러 chunk로 분할
#   ↓
# generate_embedding(chunk)로 각 chunk를 숫자 목록으로 변환
#   ↓
# 다음 lesson에서 사용자 질문 embedding과 chunk embedding을 비교
#   ↓
# 질문과 의미가 가장 가까운 chunk 검색
#
# embedding은 텍스트의 의미를 표현하는 긴 숫자 목록입니다.
#
# 예:
# "Software engineers fixed memory allocation bugs."
#   ↓ embedding model
# [0.031, -0.027, 0.014, ...]
#
# 중요한 점:
# 각 숫자가 정확히 무엇을 의미하는지는 사람이 직접 해석하기 어렵습니다.
# 숫자 하나를 "행복 점수", "바다 점수"처럼 상상할 수는 있지만,
# 실제 의미는 embedding model이 학습 과정에서 스스로 정한 특징입니다.


# ---------------------------------------------------------------------------
# 1. VoyageAI client 설정
# ---------------------------------------------------------------------------

# Anthropic은 embedding 생성 API를 제공하지 않으므로 VoyageAI를 사용합니다.
#
# VoyageAI는 별도의 API key가 필요합니다.
# 프로젝트 루트의 .env 파일에 아래 내용을 추가해야 합니다.
#
# VOYAGE_API_KEY="your_key_here"
#
# API key 발급 방법은 같은 폴더에 복사한 PDF를 참고합니다.
#
# section_05_rag_and_agentic_search/VoyageAI_API_Key_Directions.pdf
load_dotenv()

# voyageai.Client()는 환경 변수 VOYAGE_API_KEY를 자동으로 읽습니다.
# 코드 안에 API key를 직접 적지 않습니다.
client = voyageai.Client()


# ---------------------------------------------------------------------------
# 2. Chunk by section
# ---------------------------------------------------------------------------

def chunk_by_section(document_text):
    # lesson 01에서 사용했던 Markdown section chunking 함수입니다.
    #
    # 정규식 r"\n## "의 의미:
    #
    # \n : 줄바꿈
    # ## : Markdown의 두 번째 레벨 제목
    #
    # report.md를 ## 제목 기준으로 나눠서 의미 있는 section chunk를 만듭니다.
    pattern = r"\n## "
    return re.split(pattern, document_text)


# ---------------------------------------------------------------------------
# 3. Embedding generation
# ---------------------------------------------------------------------------

def generate_embedding(text, model="voyage-3-large", input_type="query"):
    # 텍스트 하나를 VoyageAI embedding model에 보내 숫자 목록으로 변환합니다.
    #
    # 파라미터:
    #
    # text:
    #   embedding으로 바꿀 문자열입니다.
    #   사용자 질문이나 문서 chunk를 넣을 수 있습니다.
    #
    # model:
    #   사용할 VoyageAI embedding model 이름입니다.
    #   원본 강의와 동일하게 "voyage-3-large"를 사용합니다.
    #
    # input_type:
    #   embedding model에게 이 텍스트의 용도를 알려줍니다.
    #
    #   "query":
    #       검색 질문처럼 취급합니다.
    #
    #   "document":
    #       검색 대상 문서처럼 취급합니다.
    #
    # 이번 강의는 embedding 숫자를 처음 확인하는 단계라
    # 원본 노트북과 동일하게 기본값 "query"를 사용합니다.
    #
    # client.embed()는 여러 텍스트를 한 번에 받을 수 있으므로 list를 넘깁니다.
    # 지금은 텍스트 하나만 처리하므로 [text] 형태입니다.
    result = client.embed(
        [text],
        model=model,
        input_type=input_type,
    )

    # result.embeddings는 embedding 목록의 목록입니다.
    #
    # 예:
    # [
    #     [0.031, -0.027, 0.014, ...]
    # ]
    #
    # 텍스트를 하나만 보냈으므로 첫 번째 embedding만 반환합니다.
    return result.embeddings[0]


# ---------------------------------------------------------------------------
# 4. 실행 예제
# ---------------------------------------------------------------------------

def run():
    # lesson 01과 같은 report.md를 읽습니다.
    report_path = Path(__file__).with_name("report.md")

    with report_path.open("r", encoding="utf-8") as file:
        text = file.read()

    # Markdown ## 제목 기준으로 문서를 section chunk로 나눕니다.
    chunks = chunk_by_section(text)

    # 첫 번째 chunk를 embedding 숫자 목록으로 바꿉니다.
    #
    # 원본 노트북은 generate_embedding(chunks[0]) 결과 전체를 출력합니다.
    # embedding은 숫자가 매우 많으므로, 터미널에서는 길이와 앞부분만 출력합니다.
    embedding = generate_embedding(chunks[0])

    print("First chunk:")
    print(chunks[0])
    print()

    print("Embedding length:")
    print(len(embedding))
    print()

    print("First 10 embedding values:")
    print(embedding[:10])
    print()

    print("The full embedding is a long list of floating-point numbers.")
    print("In the next lesson, we will compare embeddings to find relevant chunks.")
