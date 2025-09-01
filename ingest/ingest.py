import pandas as pd
from pymongo import MongoClient, ASCENDING

ORDERS_PATH = "/data/orders.csv"  # o CSV montado via volume
STORES_PATH = "/data/stores.csv"  # o CSV montado via volume
MONGO_URI = "mongodb://mongo:27017"  # nome do serviço no compose
DB_NAME = "datalk"
ORDERS_COLL_NAME = "orders"
STORES_COLL_NAME = "stores"


DATETIME_COLS = [
    "order_moment_created",
    "order_moment_accepted",
    "order_moment_ready",
    "order_moment_collected",
    "order_moment_in_expedition",
    "order_moment_delivering",
    "order_moment_delivered",
    "order_moment_finished",
]

FORMAT_US_AMPM = "%m/%d/%Y %I:%M:%S %p"


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    for col in DATETIME_COLS:
        if col in df.columns:
            # parse rápido e determinístico; strings vazias viram NaT -> depois None
            df[col] = pd.to_datetime(df[col], format=FORMAT_US_AMPM, errors="coerce")
    # trocar NaT/NaN por None para o Mongo aceitar
    df = df.replace({pd.NaT: None}).where(df.notnull(), None)
    return df


def create_indexes(coll):
    coll.create_index([("order_id", ASCENDING)], unique=True, name="uq_order_id")
    coll.create_index([("store_id", ASCENDING)], name="idx_store_id")
    coll.create_index([("channel_id", ASCENDING)], name="idx_channel_id")
    coll.create_index([("order_status", ASCENDING)], name="idx_order_status")
    coll.create_index(
        [
            ("order_created_year", ASCENDING),
            ("order_created_month", ASCENDING),
            ("order_created_day", ASCENDING),
        ],
        name="idx_created_ymd",
    )


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
        df = normalize(df)
        recs = df.to_dict(orient="records")
        orders_coll.insert_many(recs, ordered=False)
        orders += len(recs)
        print(f"Chunk {i} inserido. Total={orders}")

    print("[INGEST] Criando índices…")
    create_indexes(orders_coll)
    print("Total orders:", orders_coll.count_documents({}))

    for i, df in enumerate(
        pd.read_csv(STORES_PATH, chunksize=chunksize, sep=",", encoding="latin-1"),
        start=1,
    ):
        df = normalize(df)
        recs = df.to_dict(orient="records")
        stores_coll.insert_many(recs, ordered=False)
        stores += len(recs)
        print(f"Chunk {i} inserido. Total={stores}")

    print("Total stores:", stores_coll.count_documents({}))


if __name__ == "__main__":
    main()


"""
docker exec -it datalk-api python /ingest/ingest.py
"""
