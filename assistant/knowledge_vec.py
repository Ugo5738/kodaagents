import time
import uuid

from pinecone import Pinecone
import tiktoken
from decouple import config
from django.conf import settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import S3DirectoryLoader
from more_itertools import chunked

from koda.config.base_config import openai_client as client
from koda.config.logging_config import configure_logger

logger = configure_logger(__name__)


pinecone = Pinecone(
    api_key=config("PINECONE_API_KEY"), environment=config("PINECONE_API_ENV")
)


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 10
BATCH_SIZE = 50
PINECONE_INDEX_NAME = settings.PINECONE_INDEX_NAME


# ------------------------ UTIL FUNCTIONS ----------------------
async def get_text(knowledge_dir):
    def tiktoken_len(text):
        # Tokenize and split text
        tokenizer = tiktoken.get_encoding("cl100k_base")
        tokens = tokenizer.encode(text, disallowed_special=())
        return len(tokens)

    # Load data
    loader = S3DirectoryLoader(
        bucket=settings.AWS_STORAGE_BUCKET_NAME,
        prefix=f"media/scraped_data/{knowledge_dir}/",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    data = loader.load()
    logger.info("Done getting texts from s3 knowledge datastore")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=tiktoken_len,
        separators=["\n\n", "\n", " ", ""],
    )
    texts = text_splitter.split_documents(data)
    logger.info("Done splitting data into texts")
    return texts


async def create_embedding(text):
    response = client.embeddings.create(input=[text], model="text-embedding-ada-002")
    text_embedded = response.data[0].embedding
    return text_embedded


async def save_vec_to_database(knowledge_dir, first_db_opt=False):
    logger.info(f"Save-to-vec process started")

    if first_db_opt and PINECONE_INDEX_NAME in pinecone.list_indexes():
        logger.info(f"Deleting existing index: {PINECONE_INDEX_NAME}")
        pinecone.delete_index(PINECONE_INDEX_NAME)

    if PINECONE_INDEX_NAME not in pinecone.list_indexes():
        logger.info(f"Creating new index: {PINECONE_INDEX_NAME}")
        pinecone.create_index(PINECONE_INDEX_NAME, dimension=1536)

    pinecone_index = pinecone.Index(index_name=PINECONE_INDEX_NAME)
    text_chunks = await get_text(knowledge_dir)
    embeddings = []

    for i, chunk in enumerate(text_chunks):
        id = uuid.uuid4().hex
        content_embedded = await create_embedding(chunk.page_content)
        embedding = (id, content_embedded, {"text": chunk.page_content})
        embeddings.append(embedding)
        logger.info(f"Appended embedding chunk {i}")

    # Split the embeddings into smaller chunks (e.g., 50 vectors per request)
    for i, batch in enumerate(chunked(embeddings, BATCH_SIZE)):
        logger.info(f"Uploaded Batch {i}")
        pinecone_index.upsert(batch)


async def query_vec_database(query, num_results):
    start_time = time.time()
    query = f"Across all Canadian provinces, regarding healthcare job regulations and opportunities: {query}"
    query_embedding = await create_embedding(query)

    pinecone_index = pinecone.Index(index_name=PINECONE_INDEX_NAME)

    try:
        results = pinecone_index.query(
            query_embedding, top_k=num_results, include_metadata=True
        )
    except Exception as e:
        logger.error(f"Error querying Pinecone index: {e}")
        return []

    duration = time.time() - start_time
    logger.info(f"QUERY VEC DURATION: {duration:.2f} seconds")

    contexts = [results["matches"][0], results["matches"][1], results["matches"][2]]
    return contexts


# print(results["matches"][0]['metadata']['text'])
#     print(results["matches"][0]['score'])
