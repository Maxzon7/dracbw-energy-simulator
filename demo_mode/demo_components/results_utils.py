def get_season(month: int, country: str) -> str:
    """Returns the season based on hemisphere (Argentina is Southern Hemisphere)."""
    is_south = "Argentina" in country
    if month in [12, 1, 2]:
        return "Summer" if is_south else "Winter"
    elif month in [3, 4, 5]:
        return "Autumn" if is_south else "Spring"
    elif month in [6, 7, 8]:
        return "Winter" if is_south else "Summer"
    else:
        return "Spring" if is_south else "Autumn"
