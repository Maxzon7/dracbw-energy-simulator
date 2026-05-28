# logic/storage_manager.py
import pandas as pd
import json
import zipfile
import io

def create_drac_export(scenarios_dict: dict) -> bytes:
    """
    Compresses multiple scenarios (e.g., a Baseline + all its Sub-scenarios) 
    into a unified .drac binary archive. Creates internal folders for each.
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for scen_name, scen_data in scenarios_dict.items():
            # Create a safe internal folder name
            folder = scen_name.replace("/", "_").replace("\\", "_")
            
            df = scen_data.get("df")
            if df is not None:
                parquet_buffer = io.BytesIO()
                df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
                zip_file.writestr(f"{folder}/data.parquet", parquet_buffer.getvalue())
                
            # Clean up the metadata
            metadata = {k: v for k, v in scen_data.items() if k != "df"}
            zip_file.writestr(f"{folder}/metadata.json", json.dumps(metadata, default=str))
            
    return zip_buffer.getvalue()

def parse_drac_import(uploaded_file, import_prefix="") -> dict:
    """
    Extracts and rebuilds a scenario vault object (potentially containing an entire tree)
    from an uploaded .drac file.
    """
    reconstructed_scenarios = {}
    
    with zipfile.ZipFile(uploaded_file, "r") as zip_file:
        paths = zip_file.namelist()
        
        # Find unique scenario folders inside the zip
        folders = set([p.split("/")[0] for p in paths if "/" in p])
        
        # Backward compatibility for old single-scenario .drac files
        if not folders and ("metadata.json" in paths or "data.parquet" in paths):
            scen_dict = {}
            if "metadata.json" in paths:
                scen_dict.update(json.loads(zip_file.read("metadata.json").decode("utf-8")))
            if "data.parquet" in paths:
                pq_bytes = zip_file.read("data.parquet")
                scen_dict["df"] = pd.read_parquet(io.BytesIO(pq_bytes), engine="pyarrow")
            
            name = import_prefix if import_prefix else "Imported_Legacy_Scenario"
            reconstructed_scenarios[name] = scen_dict
            return reconstructed_scenarios

        # New multi-scenario tree parsing
        for folder in folders:
            scen_dict = {}
            if f"{folder}/metadata.json" in paths:
                scen_dict.update(json.loads(zip_file.read(f"{folder}/metadata.json").decode("utf-8")))
            if f"{folder}/data.parquet" in paths:
                pq_bytes = zip_file.read(f"{folder}/data.parquet")
                scen_dict["df"] = pd.read_parquet(io.BytesIO(pq_bytes), engine="pyarrow")
            
            # Apply prefix to the name to avoid overwriting existing vault data
            new_name = f"{import_prefix}{folder}" if import_prefix else folder
            
            # MAGIE: If it's a sub-scenario, we must also update its parent's name to keep the tree linked!
            if scen_dict.get("parent") and import_prefix:
                scen_dict["parent"] = f"{import_prefix}{scen_dict['parent']}"
                
            reconstructed_scenarios[new_name] = scen_dict
            
    return reconstructed_scenarios