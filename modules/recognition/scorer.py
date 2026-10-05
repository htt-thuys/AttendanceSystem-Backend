from collections import defaultdict


def compute(qdrant_results) -> list[dict]:
    if not qdrant_results:
        return []

    employee_scores = defaultdict(list)
    for point in qdrant_results:
        emp_id = point.payload.get("employee_id")
        if emp_id:
            employee_scores[emp_id].append(point.score)

    avg_scores = []
    for emp_id, scores in employee_scores.items():
        top_scores = sorted(scores, reverse=True)[:2]
        avg_score = sum(top_scores) / len(top_scores)
        avg_scores.append({"employee_id": emp_id, "score": avg_score})

    avg_scores = sorted(avg_scores, key=lambda item: item["score"], reverse=True)

    for index in range(len(avg_scores)):
        if index < len(avg_scores) - 1:
            avg_scores[index]["gap"] = avg_scores[index]["score"] - avg_scores[index + 1]["score"]
        else:
            avg_scores[index]["gap"] = avg_scores[index]["score"]

    return avg_scores
