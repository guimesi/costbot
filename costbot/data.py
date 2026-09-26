"""DataStore: lazy CSV loader for the data package (mock or real via COSTBOT_DATA_DIR)."""
import os
import pandas as pd


# ============================================================================
# Data paths
# ============================================================================
# Default: ./data (mock package). Override with COSTBOT_DATA_DIR to point the
# engine at the real package in the production environment without editing code.
DATA_DIR = os.environ.get("COSTBOT_DATA_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # repo root
    "data",
)


# ============================================================================
# Data Loading
# ============================================================================

class DataStore:
    """Lazy-loading cached data store for CSV reference data."""

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self._cache = {}

    def _load_csv(self, filename: str) -> pd.DataFrame:
        if filename not in self._cache:
            path = os.path.join(self.data_dir, filename)
            if os.path.exists(path):
                self._cache[filename] = pd.read_csv(path)
            else:
                self._cache[filename] = pd.DataFrame()
        return self._cache[filename]

    @property
    def pool(self) -> pd.DataFrame:
        return self._load_csv("ref_are_analogue_pool_v3.csv")

    @property
    def truth(self) -> pd.DataFrame:
        return self._load_csv("project_truth.csv")

    @property
    def cp30(self) -> pd.DataFrame:
        return self._load_csv("ref_cp30_combined_indices.csv")

    @property
    def frankenstein(self) -> pd.DataFrame:
        return self._load_csv("frankenstein.csv")

    @property
    def gate_costs(self) -> pd.DataFrame:
        return self._load_csv("gate_costs.csv")

    @property
    def equipment_vectors(self) -> pd.DataFrame:
        return self._load_csv("ref_equipment_vectors.csv")

    @property
    def archetype_taxonomy(self) -> pd.DataFrame:
        return self._load_csv("ref_archetype_taxonomy.csv")

    @property
    def scope_inputs(self) -> pd.DataFrame:
        return self._load_csv("ref_project_scope_inputs_v2.csv")

    @property
    def semantic_chips(self) -> pd.DataFrame:
        return self._load_csv("ref_semantic_chip_classifications.csv")

    @property
    def country_to_cp30(self) -> pd.DataFrame:
        return self._load_csv("ref_country_to_cp30_location.csv")
