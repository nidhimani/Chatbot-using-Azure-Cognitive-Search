import openai
import json
import os
import streamlit as st

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import Vector

from azure.search.documents.indexes.models import (
SearchIndex,
SearchField,
SearchFieldDataType,
SimpleField,
SearchableField,
VectorSearch,
HnswVectorSearchAlgorithmConfiguration,
)


openai.api_key = "Your Openai key"
openai.api_type = 'Your api type'
openai.api_base = 'Your api base'
openai.api_version = 'Your api version'

service_endpoint="Your Azure endpoint"
key="Your access key"
index_name='supplychain1'

import PyPDF2
text_data=[]
# Extract text content from PDF
pdf_path = r"C:\Users\SrinidhiJala\Downloads\SupplyChainManagement_LuSwaminathan_2015.pdf"
with open(pdf_path, 'rb') as pdf_file:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text_content = ''.join(page.extract_text() for page in pdf_reader.pages)
    text_data.append(text_content)


def get_legal_embeddings(inp : str):
    embeddings = openai.Embedding.create(input = inp, engine = "adaembedding002")["data"][0]["embedding"]
    return embeddings



def get_legal_documents(documents):
     docs = []
     for i, text in enumerate(documents):
         docs.append(
               {"Id" : str(i+1),
                "Name" : f"document {i+1}",
                "content" : text,
                "contentVector" : get_legal_embeddings(text)})
     return docs

embed_data = get_legal_documents(text_data)

def get_legal_index(name : str):

    fields = [
        SimpleField(name="Id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="Name", type=SearchFieldDataType.String, sortable=True, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,  # Adjust dimensions as needed
            vector_search_configuration="my-vector-config",
        ),
    ]
    vector_search = VectorSearch(
        algorithm_configurations=[HnswVectorSearchAlgorithmConfiguration(name="my-vector-config", kind="hnsw")]
    )
    return SearchIndex(name=name, fields=fields, vector_search=vector_search)


credential = AzureKeyCredential(key)
index_client = SearchIndexClient(service_endpoint, credential)

index = get_legal_index(index_name)
# index_client.create_index(index)

client = SearchClient(service_endpoint, index_name, credential)
client.upload_documents(documents=embed_data)

def single_vector_search(query):
    relevent_documents=[]
    search_client = SearchClient(service_endpoint, index_name, AzureKeyCredential(key))
    vector_query = Vector(value=get_legal_embeddings(query), k=3, fields="contentVector")

    results = search_client.search(
        search_text="",
        vectors=[vector_query],
        select=["Id", "Name","content"],
    )
    for result in results:
        relevent_documents.append(result['content'])
    print('Length of relevent Documents:-',len(relevent_documents))
    return '\n'.join(relevent_documents)

def chat(query):
    doc = single_vector_search(query)
    messages = []
    messages.append({"role" : "system", "content" : "You are a friendly AI assistant designed to answer supply chain related questions" })
    delimiter = "####"
    user_content = f'''context : 
                  {delimiter} {doc} {delimiter} 

                  Query : {delimiter} {query} {delimiter}

                  Extract the answer for the given query only from the context.
                  For follow-up queries, analyze your previous response and previous context only.'''

    messages.append({"role" : "user", "content" : user_content})
    response = openai.ChatCompletion.create(temperature = 0.2, engine = "gpt35", messages = messages)
    return response.choices[0]['message']['content']
st.title("Supply Chain Chatbot")

question = st.text_input("Enter the query")

st.write(chat(question))