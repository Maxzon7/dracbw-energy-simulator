# tests/test_pdf_export.py
import unittest
import io
import pandas as pd
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tabs.tab3_components.pdf_comparison_export import compile_plotly_load_chart

class TestPdfExport(unittest.TestCase):
    def setUp(self):
        # Create mock dataframes for chart generation
        self.df = pd.DataFrame({
            "timestamp": pd.date_range(start="2022-06-01 00:00:00", periods=24, freq="h"),
            "consumption_kw": [50.0] * 24,
            "final_grid_load_kw": [40.0] * 24
        })
        self.selected_profiles = ["Variant_1"]
        self.custom_colors = {"Variant_1": "#4CAF50"}

    def test_plotly_load_chart_compilation_to_bytes(self):
        def mock_get_df(name):
            return self.df
            
        # Execute the chart compile function (which calls fig.to_image under the hood)
        img_buffer = compile_plotly_load_chart(
            self.selected_profiles,
            mock_get_df,
            self.custom_colors,
            limit=100.0
        )
        
        # Verify that it returns a valid io.BytesIO buffer
        self.assertIsInstance(img_buffer, io.BytesIO)
        img_bytes = img_buffer.getvalue()
        self.assertGreater(len(img_bytes), 0)
        
        # Check PNG header magic bytes (89 50 4E 47 0D 0A 1A 0A)
        self.assertEqual(img_bytes[:4], b'\x89PNG')

if __name__ == "__main__":
    unittest.main()
