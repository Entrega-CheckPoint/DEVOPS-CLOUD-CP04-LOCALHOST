import pandas as pd
from pymongo import MongoClient

ORDERS_PATH = "/data/orders.csv"  # o CSV montado via volume
STORES_PATH = "/data/stores.csv"  # o CSV montado via volume
MONGO_URI = "mongodb://mongo:27017"  # nome do serviço no compose
DB_NAME = "datalk"
ORDERS_COLL_NAME = "orders"
STORES_COLL_NAME = "stores"


def main():
    # 1) Conecta no Mongo (NoSQL: "DB" -> "Collection" -> "Documents JSON-like")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    orders_coll = db[ORDERS_COLL_NAME]
    stores_coll = db[STORES_COLL_NAME]

    # 2) começamos do zero neste passo
    orders_coll.drop()
    stores_coll.drop()

    chunksize = 50_000
    orders = 0
    stores = 0

    for i, df in enumerate(pd.read_csv(ORDERS_PATH, chunksize=chunksize), start=1):
        df = df.where(df.notnull(), None)
        recs = df.to_dict(orient="records")
        orders_coll.insert_many(recs, ordered=False)
        orders += len(recs)
        print(f"Chunk {i} inserido. Total={orders}")

    print("Total orders:", orders_coll.count_documents({}))

    for i, df in enumerate(
        pd.read_csv(STORES_PATH, chunksize=chunksize, sep=",", encoding="latin-1"),
        start=1,
    ):
        df = df.where(df.notnull(), None)
        recs = df.to_dict(orient="records")
        stores_coll.insert_many(recs, ordered=False)
        stores += len(recs)
        print(f"Chunk {i} inserido. Total={stores}")

    print("Total stores:", stores_coll.count_documents({}))


if __name__ == "__main__":
    main()

"""
docker exec -it datalk-api python /ingest/ingest_step2_chunks.py
"""
