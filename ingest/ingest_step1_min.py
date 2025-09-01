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

    # 2) começa do zero para teste
    orders_coll.drop()
    stores_coll.drop()

    # 3) Lê só 1.000 linhas para testar o caminho
    df_orders = pd.read_csv(ORDERS_PATH, nrows=1000)
    df_stores = pd.read_csv(STORES_PATH, sep=',', encoding='latin-1')

    # 4) Pandas usa NaN para nulos; Mongo precisa de None
    df_orders = df_orders.where(df_orders.notnull(), None)
    df_stores = df_stores.where(df_stores.notnull(), None)

    # 5) Insere
    orders_recs = df_orders.to_dict(orient="records")
    orders_coll.insert_many(orders_recs)
    stores_recs = df_stores.to_dict(orient="records")
    stores_coll.insert_many(stores_recs)

    print("Inseridos:", orders_coll.count_documents({}))
    print("Inseridos:", stores_coll.count_documents({}))


if __name__ == "__main__":
    main()


"""
docker exec -it datalk-api python /ingest/ingest_step1_min.py 
docker exec -it mongo mongosh --eval 'use datalk; db.orders.countDocuments(); db.orders.findOne();'
"""
