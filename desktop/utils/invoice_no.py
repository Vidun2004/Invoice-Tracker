"""Auto invoice numbers: INV-YYYYMMDD-XXXX. Editable by user, collision-safe."""
import random
import string
from datetime import datetime


def generate_invoice_number(prefix: str = "INV") -> str:
    day = datetime.now().strftime("%Y%m%d")
    rand = "".join(random.choices(string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789", k=4))
    return f"{prefix}-{day}-{rand}"


def is_duplicate_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return "duplicate" in s or "23505" in s or "already exists" in s or "unique" in s
