"""
Streamlit Command Center UI for MoCo Lantern.
Dual-mode interface for Case Manager research and Client intake.
"""

import streamlit as st
import pydeck as pdk
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from config import ThemeConfig, APP_NAME, APP_SUBTITLE
from data_adapter import DataAdapter, SyntheticDataSource
from rag_pipeline import RAGPipeline


class CommandCenterUI:
    """Main Streamlit application controller"""
    
    def __init__(self):
        self.theme = ThemeConfig()
        self.setup_page_config()
        self.initialize_rag_pipeline()
    
    def setup_page_config(self) -> None:
        """Configure Streamlit page settings and theme"""
        st.set_page_config(
            page_title=f"{APP_NAME} | Sturdivant AI Lab",
            page_icon="🏮",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def initialize_rag_pipeline(self) -> None:
        """Initialize RAG pipeline with synthetic data"""
        if 'rag_pipeline' not in st.session_state:
            with st.spinner("Initializing vector store..."):
                # Setup data source
                data_source = SyntheticDataSource(filepath="data/resources.json")
                adapter = DataAdapter(source=data_source)
                
                # Initialize RAG
                rag = RAGPipeline(data_adapter=adapter)
                rag.initialize_vector_store()
                
                st.session_state.rag_pipeline = rag
                st.session_state.data_adapter = adapter
    
    def apply_bioluminescent_styling(self) -> None:
        """Inject custom CSS for bioluminescent effects"""
        css_vars = self.theme.to_css_variables()
        
        css = f"""
        <style>
        :root {{
            {' '.join(f'{k}: {v};' for k, v in css_vars.items())}
        }}
        
        .stApp {{
            background-color: var(--background-dark);
        }}
        
        .metric-card {{
            background-color: var(--surface-dark);
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.1);
        }}
        
        .node-glow {{
            box-shadow: 
                0 0 10px var(--primary-glow),
                0 0 20px var(--primary-glow),
                0 0 40px var(--primary-glow);
            animation: glow var(--glow-duration) var(--ease-function) infinite alternate;
        }}
        
        @keyframes glow {{
            from {{
                box-shadow: 0 0 10px var(--primary-glow), 0 0 20px var(--primary-glow);
            }}
            to {{
                box-shadow: 0 0 20px var(--primary-glow), 0 0 40px var(--primary-glow), 0 0 60px var(--primary-glow);
            }}
        }}
        
        .stChatMessage {{
            background-color: var(--surface-dark);
            border-left: 3px solid var(--primary-glow);
        }}
        
        h1, h2, h3 {{
            color: var(--primary-glow);
        }}
        </style>
        """
        
        st.markdown(css, unsafe_allow_html=True)
    
    def render_sidebar(self) -> Dict[str, any]:
        """Render sidebar with mode selection and filters"""
        with st.sidebar:
            st.title("🏮 Sturdivant AI Lab")
            st.caption(APP_NAME)
            
            st.divider()
            
            # Mode selection
            mode = st.radio(
                "Interface Mode",
                options=["Case Manager Research", "Client Intake"],
                index=0
            )
            
            st.divider()
            
            # Filters
            st.subheader("Filters")
            
            departments = ["All", "HHS", "DHCA", "Police", "Fire", "Transportation", "Environmental Protection"]
            selected_dept = st.selectbox("Department", departments)
            
            urgency_threshold = st.slider("Min Urgency", 1, 10, 1)
            
            neighborhoods = ["All", "Silver Spring", "Bethesda", "Rockville", "Wheaton", "Germantown", "Gaithersburg"]
            selected_neighborhood = st.selectbox("Neighborhood", neighborhoods)
            
            return {
                "mode": "research" if mode == "Case Manager Research" else "intake",
                "department": None if selected_dept == "All" else selected_dept,
                "urgency_threshold": urgency_threshold,
                "neighborhood": None if selected_neighborhood == "All" else selected_neighborhood
            }
    
    def render_metrics_dashboard(self, data: pd.DataFrame) -> None:
        """Display key metrics"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Total Resources",
                value=len(data),
                delta=None
            )
        
        with col2:
            urgent_count = len(data[data['Urgency_Score'] >= 7])
            st.metric(
                label="Urgent Cases",
                value=urgent_count,
                delta=f"{(urgent_count/len(data)*100):.1f}%" if len(data) > 0 else "0%"
            )
        
        with col3:
            # Calculate average "response time" (days since timestamp)
            if 'timestamp' in data.columns:
                data['days_open'] = pd.to_datetime('now') - pd.to_datetime(data['timestamp'])
                avg_days = data['days_open'].dt.days.mean()
                st.metric(
                    label="Avg Days Open",
                    value=f"{avg_days:.1f}"
                )
            else:
                st.metric(label="Avg Response Time", value="N/A")
    
    def render_map_visualization(self, data: pd.DataFrame) -> None:
        """Render pydeck map with bioluminescent node styling"""
        if data.empty:
            st.info("No resources to display")
            return
        
        # Ensure we have the required columns
        if 'Lat' not in data.columns or 'Long' not in data.columns:
            st.error("Location data not available")
            return
        
        # Prepare data for pydeck
        map_data = data[['Lat', 'Long', 'Urgency_Score', 'Subject', 'neighborhood']].copy()
        map_data['color'] = map_data['Urgency_Score'].apply(self._get_urgency_color)
        map_data['radius'] = map_data['Urgency_Score'] * 100  # Increased for visibility
        
        # Create pydeck layer
        layer = pdk.Layer(
            'ScatterplotLayer',
            data=map_data,
            get_position='[Long, Lat]',
            get_color='color',
            get_radius='radius',
            pickable=True,
            opacity=0.8,
            stroked=True,
            filled=True,
            line_width_min_pixels=2,
            get_line_color=[0, 212, 255]  # Cyan outline
        )
        
        # Set view state (centered on Montgomery County)
        view_state = pdk.ViewState(
            latitude=39.15,
            longitude=-77.2,
            zoom=9.5,
            pitch=0
        )
        
        # Render map
        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>{Subject}</b><br/>{neighborhood}<br/>Urgency: {Urgency_Score}",
                "style": {
                    "backgroundColor": "#1a1a2e",
                    "color": "#00d4ff"
                }
            }
        ))
    
    def _get_urgency_color(self, urgency: int) -> List[int]:
        """Map urgency score to RGB color for the bioluminescent map"""
        if urgency >= 8:
            return [233, 69, 96, 200]  # Red (urgent)
        elif urgency >= 5:
            return [0, 212, 255, 200]  # Cyan (medium)
        else:
            return [22, 199, 154, 200]  # Teal (low)
            
    def render_chat_interface(self, mode: str) -> None:
        """Render chat window for Case Manager or Client mode"""
        st.subheader("💬 Chat Interface" if mode == "research" else "💬 Client Intake")
        
        # Initialize chat history
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask a question..." if mode == "research" else "How can we help you today?"):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    rag = st.session_state.rag_pipeline
                    response = rag.process_query(query=prompt, mode=mode, k=5)
                    
                    # 1. DISPLAY THE TEXT IMMEDIATELY
                    full_response = response.answer
                    st.markdown(full_response)
                    
                    # 2. DISPLAY CITATIONS
                    if response.citations:
                        with st.expander("View Research Sources"):
                            for i, citation in enumerate(response.citations, 1):
                                st.write(f"{i}. **{citation.sr_id}**: {citation.policy_reference}")
                    
                    # 3. APPEND TO HISTORY
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": full_response
                    })

    def run(self) -> None:
        """Main application loop"""
        # Apply styling
        self.apply_bioluminescent_styling()
        
        # Render sidebar and get settings
        settings = self.render_sidebar()
        
        # Main content area
        st.title(f"🏮 {APP_NAME}")
        st.caption(f"{APP_SUBTITLE} | Sturdivant AI Lab")
        
        # Load data for visualization
        adapter = st.session_state.data_adapter
        documents = adapter.get_documents()
        
        # Convert to DataFrame
        data = pd.DataFrame([doc.metadata for doc in documents])
        
        # Apply filters
        if settings['department']:
            data = data[data['Department'] == settings['department']]
        if settings['urgency_threshold'] > 1:
            data = data[data['Urgency_Score'] >= settings['urgency_threshold']]
        if settings['neighborhood']:
            data = data[data['neighborhood'] == settings['neighborhood']]
        
        # Render metrics
        self.render_metrics_dashboard(data)
        
        st.divider()
        
        # Two-column layout
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📍 Resource Map")
            self.render_map_visualization(data)
        
        with col2:
            self.render_chat_interface(settings['mode'])


if __name__ == "__main__":
    app = CommandCenterUI()
    app.run()