from core.config import settings

_client = None


def get_qdrant_client():
    global _client
    if _client is None:
        from qdrant_client import QdrantClient

        _client = QdrantClient(url=settings.QDRANT_URL)
    return _client


def ensure_collection_exists():
    from qdrant_client.models import Distance, VectorParams

    client = get_qdrant_client()
    existing = [collection.name for collection in client.get_collections().collections]

    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=512, distance=Distance.COSINE),
        )


def check_qdrant_connection() -> None:
    client = get_qdrant_client()
    client.get_collections()


def search_vectors(
    vector: list[float],
    top: int = 5,
    only_active: bool = True,
    employee_id: int | None = None,
) -> list:
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client = get_qdrant_client()
    must_conditions = []

    if only_active:
        must_conditions.append(FieldCondition(key="is_active", match=MatchValue(value=True)))

    if employee_id is not None:
        must_conditions.append(FieldCondition(key="employee_id", match=MatchValue(value=employee_id)))

    query_filter = Filter(must=must_conditions) if must_conditions else None

    result = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=vector,
        limit=top,
        query_filter=query_filter,
        with_payload=True,
    )
    return result.points


def upsert_vector(point_id: int, vector: list[float], payload: dict) -> None:
    from qdrant_client.models import PointStruct

    client = get_qdrant_client()
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[PointStruct(id=point_id, vector=vector, payload=payload)],
    )


def set_vector_active(point_id: int, is_active: bool) -> None:
    set_vectors_active([point_id], is_active)


def set_vectors_active(point_ids: list[int], is_active: bool) -> None:
    if not point_ids:
        return

    client = get_qdrant_client()
    client.set_payload(
        collection_name=settings.QDRANT_COLLECTION,
        payload={"is_active": is_active},
        points=point_ids,
    )


def delete_vectors(point_ids: list[int]) -> None:
    if not point_ids:
        return

    from qdrant_client.models import PointIdsList

    client = get_qdrant_client()
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=PointIdsList(points=point_ids),
    )


def list_point_ids(limit: int = 1000) -> list[int]:
    client = get_qdrant_client()
    point_ids: list[int] = []
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            limit=limit,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        point_ids.extend(int(point.id) for point in points)
        if offset is None:
            break

    return point_ids
