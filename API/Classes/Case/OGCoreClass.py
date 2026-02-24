import os
import json
import time
import multiprocessing
from pathlib import Path
from dask.distributed import Client

# OG-Core imports
from ogcore import output_tables as ot
from ogcore import output_plots as op
from ogcore.execute import runner
from ogcore.parameters import Specifications
from ogcore.utils import safe_read_pickle

from Classes.Base import Config
from Classes.Base.FileClass import File

class OGCoreClass:
    """
    OGCoreClass manages the orchestration of the OG-Core macroeconomic model 
    runs from the MUIOGO API backend. It acts as the bridge between 
    scenario execution requests and the underlying simulation engine.
    """
    def __init__(self, case, og_spec=None):
        self.case = case
        self.og_spec = og_spec if og_spec else {}
        
        # Directories to save data inside standard MUIO structure
        self.casePath = Path(Config.DATA_STORAGE, case)
        self.resultsPath = Path(self.casePath, 'res')
        
        self.base_dir = Path(self.resultsPath, "OUTPUT_BASELINE")
        self.reform_dir = Path(self.resultsPath, "OUTPUT_REFORM")
        self.plots_dir = Path(self.resultsPath, "OG-Core_example_plots")
        self.output_csv = Path(self.resultsPath, "OG-Core_example_output.csv")
        
        # Ensure result directories exist
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.reform_dir, exist_ok=True)
        os.makedirs(self.plots_dir, exist_ok=True)

    def execute_run(self, baseline=True, reform=False):
        """
        Executes the OG-Core model based on the specifications.
        """
        run_start_time = time.time()
        
        # Initialize multiprocessor client
        num_workers = min(multiprocessing.cpu_count(), 7)
        client = Client(n_workers=num_workers, threads_per_worker=1)

        try:
            if baseline:
                print(f"[{self.case}] Starting OG-Core BASELINE run...")
                p = Specifications(
                    baseline=True,
                    num_workers=num_workers,
                    baseline_dir=str(self.base_dir),
                    output_base=str(self.base_dir),
                )
                if self.og_spec:
                    p.update_specifications(self.og_spec)
                
                runner(p, time_path=True, client=client)

            if reform:
                print(f"[{self.case}] Starting OG-Core REFORM run...")
                p2 = Specifications(
                    baseline=False,
                    num_workers=num_workers,
                    baseline_dir=str(self.base_dir),
                    output_base=str(self.reform_dir),
                )
                if self.og_spec:
                    p2.update_specifications(self.og_spec)
                
                runner(p2, time_path=True, client=client)

            if baseline and reform:
                self._generate_outputs()

        except Exception as e:
            print(f"Error executing OG-Core: {e}")
            raise
        finally:
            client.close()
            print(f"[{self.case}] Run completed in {(time.time() - run_start_time):.2f}s")
            
    def _generate_outputs(self):
        """
        Generates standard csv outputs and plots based on the baseline/reform runs.
        """
        print(f"[{self.case}] Generating OG-Core Output Aggregates and Plots...")
        
        base_tpi = safe_read_pickle(os.path.join(self.base_dir, "TPI", "TPI_vars.pkl"))
        base_params = safe_read_pickle(os.path.join(self.base_dir, "model_params.pkl"))
        
        reform_tpi = safe_read_pickle(os.path.join(self.reform_dir, "TPI", "TPI_vars.pkl"))
        reform_params = safe_read_pickle(os.path.join(self.reform_dir, "model_params.pkl"))
        
        # Determine start year or fallback to default
        start_year = self.og_spec.get("start_year", 2021)
        
        ans = ot.macro_table(
            base_tpi,
            base_params,
            reform_tpi=reform_tpi,
            reform_params=reform_params,
            var_list=["Y", "C", "K", "L", "r", "w"],
            output_type="pct_diff",
            num_years=10,
            start_year=start_year,
        )
        
        # Save table to CSV
        ans.to_csv(self.output_csv)
        
        # Auto-plot variables
        op.plot_all(
            str(self.base_dir),
            str(self.reform_dir),
            str(self.plots_dir)
        )
