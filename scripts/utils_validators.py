
def validate_positive_int(value, default, name="parameter"):
    """
    Проверяет, что value — положительное целое.
    Если нет — возвращает default и пишет предупреждение.
    """
    if not isinstance(value, int) or value <= 0:
        print(f"⚠️ Invalid {name}={value}, fallback to default ({default})")
        return default
    return value
