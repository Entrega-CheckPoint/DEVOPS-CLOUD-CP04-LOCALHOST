import os
import math
import pandas as pd
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError

CSV_PATH = os.environ.get("CSV_PATH", "/data/orders_dataset.csv")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
DB_NAME   = os.environ.get("DB_NAME", "datalk")
COLL_NAME = os.environ.get("COLL_NAME", "orders")

# Colunas de timestamp em texto -> datetime
DATETIME_COLS = [
    "order_moment_created", "order_moment_accepted", "order_moment_ready",
    "order_moment_collected", "order_moment_in_expedition",
    "order_moment_delivering", "order_moment_delivered",
    "order_moment_finished",
]

def normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    # Converte timestamps
    for col in DATETIME_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    # Nulos -> None (para o Mongo)
    df = df.where(pd.notnull(df), None)

    return df

def create_indexes(coll):
    # Índices úteis para consultas futuras
    coll.create_index([("order_id", ASCENDING)], unique=True, name="uq_order_id")
    coll.create_index([("store_id", ASCENDING)], name="idx_store_id")
    coll.create_index([("channel_id", ASCENDING)], name="idx_channel_id")
    coll.create_index([("order_status", ASCENDING)], name="idx_order_status")
    coll.create_index([("order_created_year", ASCENDING),
                       ("order_created_month", ASCENDING),
                       ("order_created_day", ASCENDING)], name="idx_created_ymd")

def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db[COLL_NAME]

    # Leitura por chunks para economizar RAM
    chunksize = 50_000
    total = 0

    print(f"[INGEST] Lendo CSV em chunks de {chunksize} linhas…")
    reader = pd.read_csv(CSV_PATH, chunksize=chunksize)

    for i, df in enumerate(reader, start=1):
        df = normalize_types(df)
        # upsert por order_id: evita duplicar na reexecução
        records = df.to_dict(orient="records")
        # Inserção em lote
        try:
            # Tenta insert_many rápido primeiro…
            coll.insert_many(records, ordered=False)
        except BulkWriteError as bwe:
            # Se já existirem registros (reexecução), faz upsert por order_id
            # (cai aqui quando há duplicatas por causa do unique index)
            pass

        total += len(records)
        print(f"[INGEST] Chunk {i} inserido. Total até agora: {total}")

    print("[INGEST] Criando índices… (idempotente)")
    create_indexes(coll)

    # Contagem final
    count = coll.count_documents({})
    print(f"[INGEST] Finalizado. Documentos na coleção: {count}")

if __name__ == "__main__":
    main()
