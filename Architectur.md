# DRACBV Green Energy Simulator - Architecture & Navigation Guide

## 1. System Overview
The Pro Energy Simulator is a parametric, scalable scenario-analysis tool developed in Python and orchestrated via Streamlit. It evaluates facility energy profiles, grid capacities, and physical system simulations (Solar PV, BESS, and Backup Generators) on a quarter-hourly basis (34,560 data intervals per year). 

To ensure optimal performance and prevent unnecessary application execution loops (reruns), the application utilizes strict structural encapsulation through Streamlit Forms (`st.form`) and an object-oriented domain data model.

---

## 2. Technical Directory & Project Structure

### Core Files
* **`app.py`**: The central execution orchestrator. Initializes global session states, handles sidebar global settings (localization and financial evaluation toggles), and routes traffic between the main project lobby and the multi-tab simulation workspace.
* **`requirements.txt`**: Defines application dependencies, including analytical components (`pandas`, `numpy`, `plotly`) and formatting systems.
* **`packages.txt` & `start_app.bat`**: Deployment environments and localized startup sequences.

### `classes/` (Domain Data Models)
* **`models.py`**: Contains the object-oriented state architecture of the application:
  * `Tariff`: Encapsulates grid connection parameters, capacity thresholds, fixed annual costs, and peak penalty matrices.
  * `FinancialParams`: Manages capital expenditure (CAPEX), operating expenses (OPEX), lifespan constraints, compounding inflation, and utility price indexing.
  * `SubScenario`: Represents a technical solution variant (e.g., Battery Storage or Solar Integration) containing simulated time-series outputs and investment metrics.
  * `BaseScenario`: The foundational parent profile for a specific client site, anchoring the raw load profile and referencing all simulated alternative children sub-scenarios.

### `logic/` (Analytical Core Engine)
* **`storage_manager.py`**: The secure state-bridge. Directs the persistence of parent-child scenario classes within Streamlit's execution memory without performance degradation.
* **`energy_logic.py`**: Contains the rigorous physical dispatch loops:
  * `get_exact_minimum_requirements`: An algorithmic "Infinite Ghost Battery" loop calculating the mathematical minimum power and capacity bounds required to shave load peaks.
  * `simulate_battery_logic`: Simulates localized BESS charging windows, round-trip efficiency losses, state-of-charge constraints, and automated peak shaving.
  * `simulate_generator_logic`: Governs backup generation runtime dynamics and calculates real-time volumetric fuel consumption penalties.

### `tabs/` (User Interface Modules)
* **`hub_menu.py`**: The "Hotel Lobby". Manages workspace level serialization via binary streams (`.drac` extensions utilizing pickle) allowing full project save, download, restore, and delete routines.
* **`tab0_overview.py`**: The executive portfolio overview displaying system-wide status logs and direct report export gates.
* **`tab1_baseline.py`**: Configures status-quo parameters. Wrapped in a primary network-safe form to suppress data-entry layout refreshes.
* **`tab2_scenarios.py`**: Integrates hardware specifications (PV arrays, inverters, storage capacities) with automated background computation threads and real-time visualization fields.
* **`tab3_comparison.py`**: Analytical engine conducting physical multi-trace overlays, load delta analytics, and multi-year comparative financial evaluations.
* **`tab4_control_center.py`**: Workspace data management, mapping structural Python classes to transferrable JSON definitions for system backups.

---

## 3. Data Integrity & Performance Guardrails

### Form Execution Control (`st.form`)
To mitigate Streamlit’s native behavior of executing full script-refreshes on every single user input alteration, all critical data entry modules (such as Tariff definitions in Tab 1 and Tab 3) are bound inside transactional form boundaries. Widget state-changes are kept isolated until a user explicitly triggers a profile processing commit.

### Analytical Downsampling & Memory Management
Time-series data frames handle massive interval records natively. Deep charting processes leverage optimized WebGL renderers (`go.Scattergl`) to prevent browser frame-rate drops when rendering complex 365-day operations.





# DRACBV Green Energy Simulator - Technical Architecture & Logic Reference

## 1. System Overview
The DRACBV Green Energy Simulator is a parametric, scalable scenario-analysis application built using Python and orchestrated via Streamlit. The core objective of the platform is to simulate, evaluate, and financially compare alternative energy supply configurations (Solar PV, Battery Energy Storage Systems [BESS], and Backup Generators) against a baseline status-quo energy profile. 

The application executes calculations on a quarter-hourly basis, processing 34,560 distinct data intervals per operational year to accurately capture power peaks, load curves, and financial impacts over a 15-year project horizon.

---

## 2. Project Directory & Component Mapping

### Core Orchestration
* **`app.py`**: The main execution entry point. It initializes global session memory states, configures sidebar settings (such as localized translation vectors and financial evaluation flags), and acts as the top-level router between the project initialization screen and the multi-tab workstation.

### Domain Data Layer (`classes/`)
* **`models.py`**: Definement of object-oriented data structures using standard Python dataclasses:
  * `Tariff`: Encapsulates grid contract structures, capacity thresholds, fixed annual infrastructure fees, and monthly peak power penalty rates.
  * `FinancialParams`: Anchors all investment parameters including Capital Expenditure (CAPEX), Operational Expenditure (OPEX), project lifetimes, inflation indices, and utility rate growth projections.
  * `SubScenario`: Represents a specific simulated technology configuration (child layer), binding the resulting optimized load profile arrays to their specific technological parameters.
  * `BaseScenario`: The foundational root object (parent layer) representing a specific facility. It anchors the verified historical consumption profile and maintains an array of all associated alternative `SubScenario` entities.

### Analytical Core Engine (`logic/`)
* **`storage_manager.py`**: Handles the persistence and retrieval of nested parent-child scenario objects inside the web server's state memory without execution lag.
* **`energy_logic.py`**: Houses the mathematical core of the application:
  * `get_exact_minimum_requirements`: Runs an iterative matrix scan over the load profile to calculate the absolute minimum battery power (kW) and capacity (kWh) required to compress consumption spikes below a set ceiling.
  * `simulate_battery_logic`: The active dispatch engine simulating state-of-charge tracking, inverter limits, charging window restrictions, and self-consumption prioritization.
  * `simulate_generator_logic`: Simulates backup generator dispatch schedules and computes localized fuel consumption penalties.

---

## 3. The 5-Phase Functional Data Lifecycle

### Phase 1: Allocation and Project Setup
When a user launches the application, `app.py` triggers `init_session_states()`, reserving dedicated memory blocks within `st.session_state`. If the user initiates a new project or restores an existing one via `.drac` binary stream uploads in `hub_menu.py`, the storage system registers a new project workspace. This layout isolates concurrent project records and prevents data crossover.

### Phase 2: Ingestion, Cleanup, and Baseline Structuring
In Tab 1, raw time-series datasets are introduced either through synthetic profile generation or file uploads. 
1. **Parsing**: The ingest engine scans the files, leveraging synonym matrices to automatically detect date-time coordinates and consumption metrics.
2. **Merging**: If the data source splits dates and times into separate fields, the ingestion logic merges them into a unified time string and parses them into a standardized ISO date-time index.
3. **Normalization**: Volumetric inputs are automatically scaled. Periodic energy deltas (kWh) are scaled to match their instantaneous average power equivalents (kW) relative to the recording interval. Numerics are cast down to `float32` to minimize memory overhead.
4. **Filing**: The processed timeline array is attached to a freshly instantiated `BaseScenario` object, establishing the historical status-quo benchmark for all subsequent optimization tracks.

### Phase 3: Hardware Simulation and Dispatch Loops
In Tab 2, technology modules are applied to the active baseline. Calculations run dynamically across the active dataframe:
* **Solar PV**: Leverages longitude and latitude inputs to fetch GHI weather matrices ($W/m^2$). It downsamples the data to 15-minute intervals, applies transposition multipliers based on panel tilt and orientation, and introduces seasonal midday thermal penalties.
* **BESS Logic**: Executes a sequential simulation step over the 34,560 intervals. At each step, the algorithm restricts battery action based on explicit boundary conditions:
  $$	ext{Discharge Limit} = \min(	ext{Required Peak Shaving}, 	ext{Inverter Power Rating}, 	ext{Available Energy in SoC})$$
  $$	ext{Charge Limit} = \min(	ext{Available Grid Headroom}, 	ext{Inverter Power Rating}, 	ext{Available Volume in SoC})$$
  The State-of-Charge (SoC) updates step-by-step, factoring in round-trip efficiency losses during energy transitions.

### Phase 4: Variant Persistence and Registration
Once a tech simulation meets the desired criteria, the user commits the layout. The system instantiates a new `SubScenario` object, binds the technical setup parameters and the calculated time-series data array, and passes it to `add_sub_scenario()`. This hooks the variant directly into the active baseline memory tree as an available optimization track.

### Phase 5: Long-Term Financial Evaluation
Tab 3 compiles the complete technical portfolio. If financials are enabled, the system computes a 15-year cashflow matrix for each variant against the root baseline:
* **CAPEX**: Recorded as a negative investment step in Year 0.
* **OPEX & Fuel**: Scaled annually using compounding inflation indices.
* **Savings**: Computed by subtracting the variant's grid fee requirements from the baseline's cost profile, scaled by utility price inflation, and discounted against the degradation curve of the hardware.
* **Break-Even Analysis**: Runs an iterative scan over the cumulative cashflow array to identify the exact operating year where the investment yields a positive net position.

---

## 4. Performance Guardrails

### Transactional Input Suppression (`st.form`)
Streamlit natively reruns the entire execution script upon any interaction with a UI widget. To prevent the simulation from constantly recalculating a 34,560-row dataframe while a user edits parameters, data input zones are wrapped in explicit `st.form` blocks. This isolates widget updates until the user commits the data package by clicking the submission button.

### Graphics Optimization (`go.Scattergl`)
Rendering thousands of time-series data points in a web layout can stall browser performance. The application replaces standard SVG trace lines with WebGL-accelerated chart components (`go.Scattergl`). This offloads graphic processing directly to the GPU, keeping user interactions smooth even during full-year analysis views.