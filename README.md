# 🏮 MoCo Lantern: Bioluminescent Civic Coordination

**Sturdivant AI Lab** | World Wide Vibes Hackathon 2026  
*Illuminating pathways through Montgomery County's social services ecosystem*

---

## 🎯 The Problem

Montgomery County residents and frontline support staff face a critical challenge: navigating complex, ever-changing eligibility requirements across dozens of social service programs. Case managers spend hours researching SNAP, housing, and utility assistance policies while vulnerable populations encounter language barriers that delay critical support. This fragmentation creates administrative bottlenecks and leaves families waiting for help they desperately need.

## 💡 The Solution

MoCo Lantern transforms social services from a fragmented model to a proactive, data-driven framework using **Generative AI and biomimetic visualization**. Our RAG-driven "Policy Co-pilot" provides instant, cited answers to eligibility questions while a bioluminescent map interface reveals resource patterns through stigmergy-based visualization—where high-demand services "glow" like deep-sea organisms, showing real-time community needs.

## ✨ The Magic Moment

Watch as the map comes alive with glowing cyan nodes representing Montgomery County resources. Ask "Does Progress Place have a food pantry?" and witness the AI instantly retrieve relevant service requests, cite official policy documents, and provide actionable guidance—all in under 3 seconds.

## 🛠️ Technology Stack

- **LLM**: Gemini 1.5 Flash (long-context policy reasoning)
- **Vector Database**: ChromaDB (768-dimensional embeddings)
- **Framework**: Python + Streamlit
- **Visualization**: Pydeck (WebGL-based bioluminescent nodes)
- **Development**: Built with Kiro AI Assistant
- **Data**: Synthetic Montgomery County 311 Service Requests (50 records with enhanced fields)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Gemini API Key ([Get one free](https://aistudio.google.com/app/apikey))

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd Sturdivant-AI-Lab-MoCo-Copilot
```

2. **Create and activate virtual environment**
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Mac/Linux
python -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure API key**
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_key_here
```

5. **Generate synthetic data**
```bash
python src/seed_data.py
```

6. **Launch MoCo Lantern**
```bash
streamlit run src/main.py
```

The app will open at `http://localhost:8501`

## 🎨 Features

### Phase 1: Policy Co-pilot (RAG-Driven)
- ✅ Instant, cited answers to SNAP/Housing/Utility eligibility questions
- ✅ ChromaDB vector store with Montgomery County 311 data
- ✅ 100% citation requirement for public trust
- ✅ Retrieval-augmented generation with Gemini 1.5 Flash

### Phase 2: Multilingual Intake
- ✅ AI Screening Bot with auto-categorization
- ✅ Support for English, Spanish, Amharic (in data model)
- ✅ Generates "Symptom & Need" briefs for Case Managers

### Visual Identity: Bioluminescent Theme
- ✅ Stigmergy-based visualization with glowing nodes
- ✅ Resource trails showing collective staff activity
- ✅ Dark-mode interface with cyan/teal accent colors
- ✅ Urgency-based color coding (red for urgent, cyan for medium, teal for low)

## 📊 Architecture

```
MoCo Lantern
├── src/
│   ├── main.py              # Streamlit Command Center UI
│   ├── rag_pipeline.py      # RAG orchestration with Gemini
│   ├── data_adapter.py      # Modular data source abstraction
│   ├── seed_data.py         # Synthetic data generator
│   └── config.py            # Bioluminescent theme configuration
├── data/
│   └── resources.json       # 50 synthetic service requests
├── assets/
│   └── styles.css           # Bioluminescent CSS animations
├── docs/
│   └── PRD.md              # Product Requirements Document
└── chroma_db/              # Vector store (auto-generated)
```

## 🎬 Demo Workflow

1. **Launch the app** - See the bioluminescent map with 50 glowing resource nodes
2. **View metrics** - Total resources, urgent cases, average days open
3. **Select mode** - Choose "Case Manager Research" or "Client Intake"
4. **Ask a question** - "Does Progress Place have a food pantry?"
5. **Get AI response** - Instant answer with citations to official policy documents
6. **Explore the map** - Click nodes to see resource details with urgency-based colors

## 🔬 Innovation: Stigmergy-Based Visualization

Inspired by ant colonies and bioluminescent organisms, MoCo Lantern uses **stigmergy**—indirect coordination through environmental traces. High-demand resources "glow" brighter, creating visual "trails" that reveal community needs in real-time. This biomimetic approach helps case managers identify at-risk neighborhoods before crises peak.

## 🔐 Security & Ethics

- **Privacy**: 100% synthetic data for prototype demonstrations
- **Accountability**: Human-in-the-loop design—Case Managers verify AI summaries
- **Fidelity**: 100% citation requirement for all policy claims
- **Transparency**: All sources linked to official Montgomery County data

## 📈 Impact

MoCo Lantern addresses Montgomery County's social services challenge by:
- **Reducing research time** from hours to seconds for case managers
- **Breaking language barriers** with multilingual support
- **Visualizing service gaps** through bioluminescent mapping
- **Ensuring accuracy** with mandatory citation of official policies
- **Scaling support** without proportional staff increases

## 🏆 Hackathon Submission

**Event**: World Wide Vibes - Montgomery County GenAI Academy Hackathon  
**Team**: Sturdivant AI Lab  
**Author**: Edidiong Hector Umoh  
**Built with**: Kiro AI Assistant

## 📝 License

This project is submitted for the World Wide Vibes Hackathon 2026.

## 🙏 Acknowledgments

- Montgomery County Open Data Portal (data inspiration)
- Google Gemini API (LLM capabilities)
- ChromaDB (vector storage)
- Streamlit (rapid prototyping)
- Kiro AI (development assistance)

---

**🏮 Illuminating pathways. Empowering communities. One query at a time.**
