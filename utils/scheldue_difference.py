import datetime


def difference(dt_now: datetime, posting_time: datetime) -> tuple:
    """Принимает время и время поста и высчитывает разницу."""
    diff = (dt_now - posting_time).__abs__().total_seconds()
    dif_hours = int(diff // 3600)
    dif_minutes = int((diff % 3600) // 60)
    dif_seconds = int(diff % 60)
    return dif_hours, dif_minutes, dif_seconds
