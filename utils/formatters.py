from pathlib import Path


def format_bytes(value: int) -> str:
    if not value:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    index = 0

    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1

    if index == 0:
        return f"{int(size)} B"

    return f"{size:.2f} {units[index]}"


def format_duration(seconds: float) -> str:
    if seconds is None or seconds < 0:
        return "--:--"

    total = round(seconds)

    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"


def output_name(input_path: str) -> str:
    path = Path(input_path)

    return str(
        path.with_name(
            f"{path.stem}-compressed.mp4"
        )
    )