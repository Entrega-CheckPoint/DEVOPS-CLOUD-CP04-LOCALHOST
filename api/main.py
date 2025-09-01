from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from bson import json_util
import requests
import re, json
import os

app = FastAPI(title="DATALK Stores CRUD + Ollama")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = "datalk"
COLL_STORES = "stores"
COLL_ORDERS = "orders"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")

DICT_IGUALDADE = {
    "store_id": "id",
    "hub_id": "hub id",
    "store_name": "nome da loja",
    "store_segment": "segmento",
    "store_plan_price": "preço",
    "store_latitude": "latitud",
    "store_longitude": "logitude",
}
DICT_TIPO = {
    "store_id": "int",
    "hub_id": "int",
    "store_name": "str",
    "store_segment": "str",
    "store_plan_price": "float",
    "store_latitude": "float",
    "store_longitude": "float",
}

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
stores = db[COLL_STORES]
orders = db[COLL_ORDERS]


class AskRequest(BaseModel):
    prompt: str


# ---------- MODELO ----------
class Store(BaseModel):
    store_id: int
    hub_id: int
    store_name: str
    store_segment: str
    store_plan_price: float
    store_latitude: float
    store_longitude: float


# ---------- CRUD ----------
@app.post("/stores")
def create_store(store: Store) -> Store:
    if stores.find_one({"store_id": store.store_id}):
        raise HTTPException(400, detail="store_id já existe")
    stores.insert_one(store.dict())
    return store


@app.get("/stores/{store_id}")
def read_store(store_id: int) -> Store:
    doc = stores.find_one({"store_id": store_id})
    if not doc:
        raise HTTPException(404, detail="Loja não encontrada")
    doc["_id"] = str(doc["_id"])
    return doc


@app.put("/stores/{store_id}")
def update_store(store_id: int, store: Store):
    result = stores.update_one({"store_id": store_id}, {"$set": store.dict()})
    if result.matched_count == 0:
        raise HTTPException(404, detail="Loja não encontrada")
    return {"msg": "Loja atualizada"}


@app.delete("/stores/{store_id}")
def delete_store(store_id: int):
    result = stores.delete_one({"store_id": store_id})
    if result.deleted_count == 0:
        raise HTTPException(404, detail="Loja não encontrada")
    return {"msg": "Loja deletada"}



@app.get("/orders")
def get_orders(
    store_id: int | None = None,
    channel_id: int | None = None,
    order_status: str | None = None,
    limit: int = 10,
):
    query = {}
    if store_id is not None:
        query["store_id"] = store_id
    if channel_id is not None:
        query["channel_id"] = channel_id
    if order_status is not None:
        query["order_status"] = order_status

    cursor = orders.find(query).limit(limit)

    # Serializa com suporte a NaN/Infinity/etc.
    results = json.loads(json_util.dumps(cursor))

    return {"query": query, "results": results}


# ---------- Ollama "READ" Inteligente ----------
@app.post("/ask/stores")
def ask_stores(req: AskRequest):
    payload = {
        "model": "mistral",
        "stream": False,
        "prompt": f"""
        Você é um tradutor de linguagem natural para MongoDB.
        Responda SOMENTE com um JSON válido que represente o filtro.
        NUNCA adicione explicações ou texto fora do JSON.

        Coleção: stores
        Igualdade: {DICT_IGUALDADE}
        Tipos: {DICT_TIPO}

        Pergunta: {req.prompt}
        """,
    }
    resp = requests.post(OLLAMA_URL, json=payload)
    data = resp.json()
    text = data.get("response", "").strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise HTTPException(400, detail=f"Ollama não retornou JSON válido: {text}")
    query_str = match.group(0)

    try:
        query = json.loads(query_str)
        results = list(stores.find(query, {"_id": 0}).limit(5))
    except Exception as e:
        raise HTTPException(400, detail=f"Erro ao executar query: {e}")

    return {"prompt": req.prompt, "query": query, "results": results}
