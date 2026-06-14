from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    FAISS_DIR,
    get_api_key,
    get_base_url,
    get_chat_model,
    get_embedding_model,
    load_system_prompt,
)
from knowledge_base import load_properties, property_to_text


class RentalAssistant:
    def __init__(self, top_k: int = 4) -> None:
        api_key = get_api_key()
        if not api_key:
            raise ValueError(
                "API-ключ не найден. Укажите OPENAI_API_KEY или PROXYAPI_KEY в .env"
            )

        base_url = get_base_url()
        self.top_k = top_k
        self.system_prompt = load_system_prompt()
        self.properties = load_properties()

        embeddings = OpenAIEmbeddings(
            model=get_embedding_model(),
            api_key=api_key,
            base_url=base_url,
        )
        self.llm = ChatOpenAI(
            model=get_chat_model(),
            api_key=api_key,
            base_url=base_url,
            temperature=0.65,
        )

        if self._index_exists():
            self.vectorstore = FAISS.load_local(
                str(FAISS_DIR),
                embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            self.vectorstore = self._build_vectorstore(embeddings)

    @staticmethod
    def _index_exists() -> bool:
        return FAISS_DIR.exists() and any(FAISS_DIR.iterdir())

    def _build_vectorstore(self, embeddings: OpenAIEmbeddings) -> FAISS:
        documents = [
            Document(
                page_content=property_to_text(item),
                metadata={"property_id": item["id"], "title": item["title"]},
            )
            for item in self.properties
        ]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=700,
            chunk_overlap=80,
            separators=["\n\n", "\n", ". ", " "],
        )
        chunks = splitter.split_documents(documents)

        vectorstore = FAISS.from_documents(chunks, embeddings)
        FAISS_DIR.mkdir(parents=True, exist_ok=True)
        vectorstore.save_local(str(FAISS_DIR))
        return vectorstore

    def retrieve_context(self, question: str) -> str:
        docs = self.vectorstore.similarity_search(question, k=self.top_k)
        if not docs:
            return "В базе знаний нет подходящих объектов."

        blocks = []
        for index, doc in enumerate(docs, start=1):
            title = doc.metadata.get("title", "Объект")
            blocks.append(f"[Фрагмент {index}: {title}]\n{doc.page_content}")
        return "\n\n---\n\n".join(blocks)

    def answer(
        self,
        question: str,
        client_context: str | None = None,
    ) -> str:
        context = self.retrieve_context(question)
        client_block = ""
        if client_context:
            client_block = f"{client_context}\n\n"
        user_message = (
            f"{client_block}"
            "Контекст из базы знаний объектов недвижимости:\n"
            f"{context}\n\n"
            f"Вопрос клиента:\n{question}"
        )

        response = self.llm.invoke(
            [
                ("system", self.system_prompt),
                ("user", user_message),
            ]
        )
        content = response.content
        if isinstance(content, list):
            return "".join(str(part) for part in content).strip()
        return str(content).strip()


def build_index(force: bool = False) -> Path:
    if force and FAISS_DIR.exists():
        import shutil

        shutil.rmtree(FAISS_DIR)

    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    assistant = RentalAssistant()
    return FAISS_DIR
