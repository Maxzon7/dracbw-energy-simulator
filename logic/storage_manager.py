# logic/storage_manager.py
import pandas as pd
import json
import zipfile
import io

def create_drac_export(vault_scenario: dict) -> bytes:
    """
    Compresses a scenario dictionary (DataFrame + Metadata) into a unified .drac binary file.
    Uses Parquet for the time-series data to ensure extreme compression and fast I/O.
    """
    # 1. Create an in-memory buffer to hold the ZIP file
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        
        # 2. Convert DataFrame to Parquet and write to the ZIP archive
        df = vault_scenario.get("df")
        if df is not None:
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
            zip_file.writestr("data.parquet", parquet_buffer.getvalue())
            
        # 3. Clean up the metadata (remove the df so we don't duplicate it)
        metadata = {k: v for k, v in vault_scenario.items() if k != "df"}
        
        # Write metadata to a JSON file inside the ZIP
        zip_file.writestr("metadata.json", json.dumps(metadata, default=str))
        
    return zip_buffer.getvalue()

def parse_drac_import(uploaded_file) -> dict:
    """
    Extracts and rebuilds a scenario vault object from an uploaded .drac file.
    """
    reconstructed_scenario = {}
    
    # Read the uploaded binary as a ZIP archive
    with zipfile.ZipFile(uploaded_file, "r") as zip_file:
        
        # 1. Extract and parse metadata
        if "metadata.json" in zip_file.namelist():
            metadata_bytes = zip_file.read("metadata.json")
            reconstructed_scenario = json.loads(metadata_bytes.decode("utf-8"))
            
        # 2. Extract and rebuild the DataFrame
        if "data.parquet" in zip_file.namelist():
            parquet_bytes = zip_file.read("data.parquet")
            parquet_buffer = io.BytesIO(parquet_bytes)
            reconstructed_scenario["df"] = pd.read_parquet(parquet_buffer, engine="pyarrow")
            
    return reconstructed_scenario