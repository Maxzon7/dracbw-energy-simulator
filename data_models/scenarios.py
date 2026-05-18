class BaselineScenario:
    """
    Represents the foundational scenario containing raw data and grid constraints.
    """
    def __init__(self, name: str, raw_data: pd.DataFrame, grid_limit_kw: float):
        self.name = name
        self.raw_data = raw_data
        self.grid_limit_kw = grid_limit_kw

class SubScenario:
    """
    Represents a variation built upon a BaselineScenario.
    Stores only the delta parameters (Solar, Battery, Wind, Generator).
    """
    def __init__(self, name: str, parent_baseline: BaselineScenario):
        self.name = name
        self.parent_baseline = parent_baseline
        
        self.solar_params = None
        self.battery_params = None
        self.wind_params = None
        self.generator_params = None