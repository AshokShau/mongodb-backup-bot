from typing import List, Union
import pymongo
from pytdbot import types
import asyncio


async def get_db_list(uri: str) -> Union[List[str], types.Error]:
    """
    Fetches a list of database names from a MongoDB URI asynchronously.

    Args:
        uri: MongoDB connection URI.

    Returns:
        A list of database names or types.Error on failure.
    """
    try:
        client = pymongo.AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
        await client.aconnect()
        db_names = await client.list_database_names()
        db_names = [db for db in db_names if db not in ['admin', 'config', 'local']]
        await client.close()
        return db_names
    except Exception as e:
        return types.Error(code=400, message=str(e))
