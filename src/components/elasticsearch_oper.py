from elasticsearch import Elasticsearch
from crewai.tasks import TaskOutput
from typing import List, Type, Dict
from dotenv import load_dotenv
import os

load_dotenv()
# ✅ Elasticsearch Client Setup
esuser=os.getenv("esuser")
espassword=os.getenv("espassword")
eshost=os.getenv("eshost")
esport=os.getenv("esport")

client = Elasticsearch(
    f"https://{esuser}:{espassword}@{eshost}:{esport}",
    verify_certs=False,
    request_timeout=120
)
# ✅ Define the index name
INDEX_NAME = "test_hackathon_rbi_datewise_docs"

class ElasticSearchTool:
    name: str = "Elastic Search operations"
    description: str = "Store and retrieve operations in elastic search"
    client.indices.create(
    index=INDEX_NAME,
    ignore=400,  # Ignore if index already exists
    )

    def store_in_elastic(self, output):
        # ✅ Store in Elasticsearch
        try:
            client.index(index=INDEX_NAME, id=output['downloaded_url'], document=output)
            print("Document Indexed in Elastic Successfully")
        except Exception as e:
            print(f"Error while storing in Elastic: {e}")

