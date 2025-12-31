from typing import List, Union
import pymongo
from pymongo.errors import OperationFailure
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
        async with pymongo.AsyncMongoClient(uri, serverSelectionTimeoutMS=5000) as client:
            await client.aconnect()
            db_names = await client.list_database_names()
            db_names = [db for db in db_names if db not in ['admin', 'config', 'local']]
            return db_names
    except Exception as e:
        return types.Error(code=400, message=str(e))


async def drop_all_dbs(uri: str) -> Union[types.Ok, types.Error]:
    """
    Drops all databases (excluding system ones) from a MongoDB URI asynchronously.
    If the user lacks permission to drop the database, it attempts to drop all collections inside it.

    Args:
        uri: MongoDB connection URI.

    Returns:
        types.Ok on success, or types.Error on failure.
    """
    try:
        async with pymongo.AsyncMongoClient(uri, serverSelectionTimeoutMS=5000) as client:
            await client.aconnect()
            db_names = await client.list_database_names()
            target_dbs = [db for db in db_names if db not in ['admin', 'config', 'local']]

            for db_name in target_dbs:
                try:
                    await client.drop_database(db_name)
                except OperationFailure as e:
                    if e.code == 8000 or "not allowed to do action [dropDatabase]" in str(e):
                        try:
                            db = client[db_name]
                            collections = await db.list_collection_names()
                            for col_name in collections:
                                if not col_name.startswith("system."):
                                    await db.drop_collection(col_name)
                        except Exception as inner_e:
                            return types.Error(code=400, message=f"Failed to wipe {db_name}: {str(inner_e)}")
                    else:
                        return types.Error(code=400, message=str(e))

            return types.Ok()
    except Exception as e:
        return types.Error(code=400, message=str(e))
