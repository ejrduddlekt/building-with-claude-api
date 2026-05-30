import math
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
# RAG with a Vector Database
# ---------------------------------------------------------------------------
#
# 이번 lesson은 지금까지 배운 chunking과 embedding을 하나로 연결합니다.
#
# 전체 흐름:
#
# 1. 긴 문서를 section 단위 chunk로 나눈다.
# 2. 각 chunk를 embedding 숫자 목록으로 바꾼다.
# 3. embedding과 원본 chunk를 vector store에 함께 저장한다.
# 4. 사용자의 질문도 embedding으로 바꾼다.
# 5. 질문 embedding과 가장 가까운 chunk를 검색한다.
#
# 왜 원본 chunk도 함께 저장할까?
#
# embedding 숫자만 검색 결과로 받으면 Claude prompt에 넣을 실제 문장이 없습니다.
# 따라서 vector store에는 아래 두 값을 같이 보관해야 합니다.
#
# embedding: 의미 검색에 사용하는 숫자 목록
# document:  나중에 다시 꺼낼 실제 원본 text와 metadata


# ---------------------------------------------------------------------------
# 1. VoyageAI client setup
# ---------------------------------------------------------------------------

load_dotenv()

# .env 파일에 VOYAGE_API_KEY가 있어야 합니다.
# 코드 안에 API key를 직접 적지 않습니다.
client = voyageai.Client()


# ---------------------------------------------------------------------------
# 2. Chunking and embedding helpers
# ---------------------------------------------------------------------------

def chunk_by_section(document_text):
    # Markdown의 ## 제목을 기준으로 문서를 section chunk로 나눕니다.
    pattern = r"\n## "
    return re.split(pattern, document_text)


def generate_embedding(chunks, model="voyage-3-large", input_type="query"):
    # lesson 02에서는 문자열 하나만 embedding으로 바꿨습니다.
    #
    # 이번에는 문자열 하나와 문자열 list를 모두 처리할 수 있게 확장합니다.
    #
    # 문자열 하나:
    # generate_embedding("What did the software team do?")
    #   ↓
    # [0.01, -0.02, ...]
    #
    # 문자열 list:
    # generate_embedding(["chunk 1", "chunk 2"])
    #   ↓
    # [
    #     [0.01, -0.02, ...],
    #     [0.03, 0.04, ...],
    # ]
    is_list = isinstance(chunks, list)

    # VoyageAI client.embed()는 항상 list를 받습니다.
    # 문자열 하나가 들어오면 [chunks]로 감싸서 list로 만듭니다.
    inputs = chunks if is_list else [chunks]

    result = client.embed(
        inputs,
        model=model,
        input_type=input_type,
    )

    # 입력이 list였다면 embedding list 전체를 반환합니다.
    # 입력이 문자열 하나였다면 첫 번째 embedding만 반환합니다.
    return result.embeddings if is_list else result.embeddings[0]


# ---------------------------------------------------------------------------
# 3. Vector store
# ---------------------------------------------------------------------------

class VectorIndex:
    # 실제 서비스에서는 Pinecone, Weaviate, Qdrant 같은 vector database를
    # 사용할 수 있습니다.
    #
    # 이번 강의에서는 원리를 보기 위해 Python list만 사용합니다.
    def __init__(self, distance_metric="cosine", embedding_fn=None):
        # vectors:
        # embedding 숫자 목록들을 저장합니다.
        #
        # documents:
        # 각 embedding과 연결된 원본 chunk와 metadata를 저장합니다.
        #
        # 두 list는 같은 index를 공유합니다.
        #
        # self.vectors[0]   <-> self.documents[0]
        # self.vectors[1]   <-> self.documents[1]
        self.vectors = []
        self.documents = []
        self._vector_dim = None

        if distance_metric not in ["cosine", "euclidean"]:
            raise ValueError("distance_metric must be 'cosine' or 'euclidean'")

        self._distance_metric = distance_metric
        self._embedding_fn = embedding_fn

    def add_document(self, document):
        # embedding_fn이 설정된 경우에는 document text만 넘겨도 됩니다.
        # 이 메서드가 내부에서 embedding을 만든 뒤 add_vector()를 호출합니다.
        if not self._embedding_fn:
            raise ValueError(
                "Embedding function not provided during initialization."
            )

        if not isinstance(document, dict):
            raise TypeError("Document must be a dictionary.")

        if "content" not in document:
            raise ValueError("Document dictionary must contain a 'content' key.")

        content = document["content"]
        if not isinstance(content, str):
            raise TypeError("Document 'content' must be a string.")

        vector = self._embedding_fn(content)
        self.add_vector(vector=vector, document=document)

    def add_vector(self, vector, document):
        # 이미 만든 embedding과 원본 document를 vector store에 추가합니다.
        #
        # document 예:
        # {
        #     "content": "Section 2: Software Engineering ..."
        # }
        if not isinstance(vector, list) or not all(
            isinstance(value, (int, float)) for value in vector
        ):
            raise TypeError("Vector must be a list of numbers.")

        if not isinstance(document, dict):
            raise TypeError("Document must be a dictionary.")

        if "content" not in document:
            raise ValueError("Document dictionary must contain a 'content' key.")

        # 모든 embedding은 길이가 같아야 비교할 수 있습니다.
        # 첫 vector가 들어올 때 embedding 차원 수를 저장합니다.
        if not self.vectors:
            self._vector_dim = len(vector)
        elif len(vector) != self._vector_dim:
            raise ValueError(
                f"Inconsistent vector dimension. "
                f"Expected {self._vector_dim}, got {len(vector)}"
            )

        self.vectors.append(list(vector))
        self.documents.append(document)

    def search(self, query, k=1):
        # query와 가장 가까운 document k개를 반환합니다.
        #
        # query는 두 가지 형태를 받을 수 있습니다.
        #
        # 1. 문자열 질문:
        #    "What did the software engineering department do?"
        #
        # 2. 이미 생성된 embedding:
        #    [0.01, -0.02, ...]
        if not self.vectors:
            return []

        if isinstance(query, str):
            if not self._embedding_fn:
                raise ValueError(
                    "Embedding function not provided for string query."
                )

            query_vector = self._embedding_fn(query)
        elif isinstance(query, list) and all(
            isinstance(value, (int, float)) for value in query
        ):
            query_vector = query
        else:
            raise TypeError(
                "Query must be either a string or a list of numbers."
            )

        if len(query_vector) != self._vector_dim:
            raise ValueError(
                f"Query vector dimension mismatch. "
                f"Expected {self._vector_dim}, got {len(query_vector)}"
            )

        if k <= 0:
            raise ValueError("k must be a positive integer.")

        if self._distance_metric == "cosine":
            distance_function = self._cosine_distance
        else:
            distance_function = self._euclidean_distance

        # 저장된 모든 embedding과 query embedding 사이의 거리를 계산합니다.
        distances = []

        for index, stored_vector in enumerate(self.vectors):
            distance = distance_function(query_vector, stored_vector)
            distances.append((distance, self.documents[index]))

        # distance가 작을수록 의미가 더 가깝습니다.
        distances.sort(key=lambda item: item[0])

        # 가까운 순서대로 k개만 반환합니다.
        return [(document, distance) for distance, document in distances[:k]]

    def _euclidean_distance(self, vector_1, vector_2):
        # 두 점 사이의 직선 거리를 계산합니다.
        if len(vector_1) != len(vector_2):
            raise ValueError("Vectors must have the same dimension")

        return math.sqrt(
            sum((value_1 - value_2) ** 2 for value_1, value_2 in zip(vector_1, vector_2))
        )

    def _dot_product(self, vector_1, vector_2):
        # cosine distance 계산에 필요한 내적입니다.
        if len(vector_1) != len(vector_2):
            raise ValueError("Vectors must have the same dimension")

        return sum(
            value_1 * value_2 for value_1, value_2 in zip(vector_1, vector_2)
        )

    def _magnitude(self, vector):
        # cosine distance 계산에 필요한 vector 크기입니다.
        return math.sqrt(sum(value * value for value in vector))

    def _cosine_distance(self, vector_1, vector_2):
        # cosine similarity는 두 vector의 방향이 얼마나 비슷한지 측정합니다.
        #
        # cosine distance = 1 - cosine similarity
        #
        # distance가 작을수록 의미가 가깝습니다.
        if len(vector_1) != len(vector_2):
            raise ValueError("Vectors must have the same dimension")

        magnitude_1 = self._magnitude(vector_1)
        magnitude_2 = self._magnitude(vector_2)

        if magnitude_1 == 0 and magnitude_2 == 0:
            return 0.0
        elif magnitude_1 == 0 or magnitude_2 == 0:
            return 1.0

        dot_product = self._dot_product(vector_1, vector_2)
        cosine_similarity = dot_product / (magnitude_1 * magnitude_2)

        # 부동소수점 계산 오차 때문에 범위를 아주 조금 벗어날 수 있습니다.
        cosine_similarity = max(-1.0, min(1.0, cosine_similarity))

        return 1.0 - cosine_similarity

    def __len__(self):
        return len(self.vectors)

    def __repr__(self):
        has_embedding_fn = "Yes" if self._embedding_fn else "No"

        return (
            f"VectorIndex(count={len(self)}, dim={self._vector_dim}, "
            f"metric='{self._distance_metric}', "
            f"has_embedding_fn='{has_embedding_fn}')"
        )


# ---------------------------------------------------------------------------
# 4. Five-step RAG example
# ---------------------------------------------------------------------------

def run():
    report_path = Path(__file__).with_name("report.md")

    with report_path.open("r", encoding="utf-8") as file:
        text = file.read()

    # Step 1. Chunk the text by section
    chunks = chunk_by_section(text)

    print("Step 1. Chunk the text by section")
    print(f"Chunk count: {len(chunks)}")
    print()

    # Step 2. Generate embeddings for every chunk
    #
    # 여러 chunk를 한 번에 보내면 API 호출 횟수를 줄일 수 있습니다.
    # 검색 대상 문서이므로 input_type="document"를 사용합니다.
    embeddings = generate_embedding(
        chunks,
        input_type="document",
    )

    print("Step 2. Generate embeddings for every chunk")
    print(f"Embedding count: {len(embeddings)}")
    print(f"Embedding dimensions: {len(embeddings[0])}")
    print()

    # Step 3. Create a vector store and add every embedding
    store = VectorIndex()

    for embedding, chunk in zip(embeddings, chunks):
        # zip()은 embedding과 원본 chunk를 한 쌍씩 묶습니다.
        #
        # 첫 번째 embedding <-> 첫 번째 chunk
        # 두 번째 embedding <-> 두 번째 chunk
        store.add_vector(
            embedding,
            {"content": chunk},
        )

    print("Step 3. Store embeddings with their original chunks")
    print(store)
    print()

    # Step 4. Generate an embedding for the user's question
    #
    # 검색 질문이므로 input_type="query"를 사용합니다.
    question = "What did the software engineering dept do last year?"
    user_embedding = generate_embedding(
        question,
        input_type="query",
    )

    print("Step 4. Generate an embedding for the user's question")
    print(question)
    print()

    # Step 5. Find the two closest chunks
    results = store.search(user_embedding, 2)

    print("Step 5. Find the two most relevant chunks")
    print()

    for document, distance in results:
        print(f"Cosine distance: {distance}")
        print(document["content"][:500])
        print()
        print("-" * 80)

