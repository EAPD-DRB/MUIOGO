\# MUIOGO — Modelling User Interface for OG‑Core \& OSeMOSYS



\## 🌍 Overview



MUIOGO is an integrated, platform‑independent decision‑support interface that unifies two widely used open‑source policy modelling ecosystems:



\* \*\*CLEWS / OSeMOSYS\*\* — sectoral resource systems modelling (Climate, Land, Energy, Water)

\* \*\*OG‑Core\*\* — dynamic overlapping‑generations macroeconomic modelling



The project extends the existing \*\*MUIO\*\* interface into a robust, scalable, and user‑friendly environment that enables policymakers, researchers, and analysts to perform \*\*standalone\*\*, \*\*coupled\*\*, and \*\*iterative converging\*\* simulations across natural resource and macroeconomic domains.



By bridging physical resource constraints with economy‑wide dynamics, MUIOGO empowers evidence‑based sustainable development planning with full transparency and reproducibility.



---



\## 🎯 Project Vision



Sustainable policy design requires understanding both:



\* Physical system feasibility (energy, land, water, climate)

\* Economy‑wide and intergenerational impacts



Currently, CLEWS/OSeMOSYS and OG‑Core operate as separate tools. \*\*MUIOGO removes this fragmentation\*\* by providing:



✅ A unified user interface

✅ Automated data exchange pipelines

✅ Standardized execution workflows

✅ Integrated visualization and reporting



This enables policymakers to evaluate trade‑offs that were previously difficult or impossible to assess in a single workflow.



---



\## 🚀 Key Objectives



\### 1. Cross‑Platform MUIO



\* Refactor the existing MUIO codebase

\* Ensure compatibility with:



&nbsp; \* Windows

&nbsp; \* macOS

&nbsp; \* Linux

\* Preserve full backward compatibility

\* Provide reproducible packaged builds



\### 2. OG‑Core Integration



\* Implement a full OG‑Core module inside MUIO

\* Mirror CLEWS feature parity

\* Provide scenario management and execution

\* Standardize outputs and logs



\### 3. Coupled OG–CLEWS Workflows



\* Enable one‑way model coupling

\* Automate data transformation pipelines

\* Store intermediate artifacts

\* Provide validation guardrails



\### 4. Converging (Iterative) Mode



\* Support multi‑iteration runs until convergence

\* Provide convergence monitoring

\* Ensure numerical stability



---



\## 🧩 System Architecture



```

┌──────────────────────────────────────────────┐

│                    MUIOGO                     │

├──────────────────────────────────────────────┤

│  User Interface Layer                        │

│  ├─ Scenario Manager                         │

│  ├─ Run Configuration                        │

│  ├─ Visualization Dashboard                  │

│  └─ Workflow Monitor                         │

├──────────────────────────────────────────────┤

│  Execution Orchestrator                      │

│  ├─ CLEWS Runner                             │

│  ├─ OG‑Core Runner                           │

│  ├─ Coupling Engine                          │

│  └─ Convergence Controller                   │

├──────────────────────────────────────────────┤

│  Data Exchange Layer                         │

│  ├─ Output → Input Transformers              │

│  ├─ Validation Checks                        │

│  └─ Intermediate Storage                     │

├──────────────────────────────────────────────┤

│  Model Backends                              │

│  ├─ OSeMOSYS / CLEWS                         │

│  └─ OG‑Core                                  │

└──────────────────────────────────────────────┘

```



---



\## 🧪 Supported Execution Modes



\### 🔹 Standalone Mode



Users can run models independently:



\* CLEWS only

\* OG‑Core only



\*\*Features\*\*



\* Scenario creation

\* Run configuration

\* Log capture

\* Interactive visualization



---



\### 🔹 Coupled Mode (One‑Way)



Workflow:



```

Model A → Transform → Model B

```



Supported directions:



\* CLEWS → OG‑Core

\* OG‑Core → CLEWS



\*\*Capabilities\*\*



\* Automatic data exchange

\* Intermediate file storage

\* Input validation

\* Step‑wise progress monitoring



---



\### 🔹 Converging Mode (Iterative)



Workflow:



```

CLEWS → OG → CLEWS → OG → … until convergence

```



\*\*Key Features\*\*



\* User‑defined tolerance

\* Iteration limits

\* Convergence diagnostics

\* Stability safeguards



---



\## 🖥️ User Interface Features



\### Scenario Management



\* Create and clone scenarios

\* Link cross‑model scenarios

\* Version tracking

\* Metadata capture



\### Run Configuration



\* Model selection

\* Coupling direction

\* Convergence settings

\* Resource allocation



\### Execution Monitoring



\* Real‑time logs

\* Progress indicators

\* Failure diagnostics

\* Guardrail warnings



\### Results \& Visualization



\* Interactive graphs

\* Standardized output structure

\* Cross‑model comparison views

\* Export capabilities



---



\## 📂 Repository Structure



```

muiogo/

├── ui/                     # Frontend components

├── orchestrator/           # Workflow engine

├── adapters/

│   ├── clews/              # CLEWS interface

│   └── ogcore/             # OG‑Core interface

├── coupling/               # Data exchange pipelines

├── convergence/            # Iterative controller

├── validation/             # Input/output checks

├── results/                # Standardized outputs

├── packaging/              # Cross‑platform builds

└── docs/                   # Documentation

```



---



\## ⚙️ Installation



\### Prerequisites



\* Python (version specified in `pyproject.toml`)

\* Git

\* Platform‑specific solvers for OSeMOSYS



\### Clone Repository



```bash

git clone https://github.com/OSeMOSYS/MUIO.git

cd MUIO

```



\### Install Dependencies



```bash

pip install -r requirements.txt

```



\### Run Application



```bash

python main.py

```



---



\## 🧠 Design Principles



\* \*\*Transparency first\*\* — all assumptions visible

\* \*\*Reproducibility\*\* — deterministic workflows

\* \*\*Usability for policymakers\*\* — sensible defaults

\* \*\*Modularity\*\* — clean separation of concerns

\* \*\*Scalability\*\* — supports country‑level deployments

\* \*\*Open‑source alignment\*\* — no proprietary lock‑in



---



\## 🌐 Real‑World Impact



The enhanced platform will support deployments in \*\*10+ countries\*\* under ongoing UN technical cooperation programmes. Expected benefits include:



\* Better Nationally Determined Contributions (NDC) planning

\* Prevention of maladaptation risks

\* Improved social protection analysis

\* Evidence‑based energy transition strategies

\* Support for low‑income country policy design



The work contributes directly to advancing the \*\*Sustainable Development Goals (SDGs)\*\* through integrated, data‑driven policy analysis.



---



\## 🛣️ Development Roadmap



\### Phase 1 — Cross‑Platform Refactor



\* \[ ] Abstract OS‑specific code

\* \[ ] Implement packaging pipeline

\* \[ ] CI for multi‑OS builds



\### Phase 2 — OG‑Core Module



\* \[ ] Scenario UI

\* \[ ] Runner integration

\* \[ ] Output standardization



\### Phase 3 — Coupled Engine



\* \[ ] Data transformers

\* \[ ] Validation layer

\* \[ ] Coupled UI workflow



\### Phase 4 — Convergence Engine



\* \[ ] Iteration controller

\* \[ ] Tolerance handling

\* \[ ] Diagnostics dashboard



\### Phase 5 — Hardening \& UX



\* \[ ] Error messaging

\* \[ ] Performance tuning

\* \[ ] Documentation polish



---



\## 🤝 Contributing



We welcome contributions from the open‑source community.



\*\*Suggested workflow:\*\*



1\. Fork the repository

2\. Create a feature branch

3\. Add tests where applicable

4\. Submit a pull request with clear description



Please ensure:



\* Code follows project style guidelines

\* All new modules include documentation

\* Workflows remain reproducible



---



\## 📜 License



This project follows the same open‑source license as the upstream MUIO repository.



---



\## 🙏 Acknowledgements



Developed under the guidance of the United Nations Department of Economic and Social Affairs (DESA), Economic Analysis and Policy Division (EAPD), and the global open‑source modelling community.



---



\## ⭐ Why MUIOGO Matters



> Bridging physical resource systems with macroeconomic dynamics enables a new generation of transparent, evidence‑based policymaking tools for sustainable development.



If this project supports your research or policy work, consider starring the repository and contributing to its growth.



---



\*\*Built for policymakers. Designed for transparency. Engineered for impact.\*\* 🚀



