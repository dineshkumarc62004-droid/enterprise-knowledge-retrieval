
import os
import ollama

MODEL_NAME = "qwen2.5:3b"

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434",
)

ollama_client = ollama.Client(host=OLLAMA_HOST)


def generate_answer(question: str, context_chunks: list[dict]) -> str:
    """Generate a clear answer using only retrieved document content."""

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    valid_chunks = [
        item for item in context_chunks
        if item.get("text") and item["text"].strip()
    ]

    if not valid_chunks:
        return "Not found in the provided documents."

    context_parts = []

    for index, item in enumerate(valid_chunks, start=1):
        context_parts.append(
            f"""
DOCUMENT {index}
Filename: {item.get('filename', 'Unknown')}
Content:
{item['text']}
"""
        )

    context = "\n".join(context_parts)

    prompt = f"""
You are an accurate Enterprise Knowledge Retrieval assistant.

Your task is to answer the user's question using the document content below.

STRICT RULES:
1. Read all the provided document content carefully.
2. Find information related to the question.
3. If relevant information is available, provide a direct and useful answer.
4. Combine information from multiple document sections when necessary.
5. Do not answer with only document names, chunk numbers, or metadata.
6. Do not copy the entire document content.
7. Do not invent information or use outside knowledge.
8. If the documents contain only partial information, explain what is available.
9. Reply "Not found in the provided documents." only when no relevant information is available.
10. Use simple, clear English.
11. Use bullet points when explaining multiple rules or steps.
12. Return only the answer. Do not include internal reasoning.

DOCUMENT CONTENT:
{context}

USER QUESTION:
{question}

FINAL ANSWER:
"""

    response = ollama_client.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={
            "temperature": 0,
            "num_predict": 400,
        },
    )

    answer = response["message"]["content"].strip()

    return answer or "Not found in the provided documents."
