#!/usr/bin/env python3
"""
NiceGUI Interface for N-Dimensional Spectra Visualization
Provides interactive visualization of survey results, projections, and comparisons.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde

from nicegui import ui, app
from nicegui.events import ValueChangeEventArguments

# Configuration
API_BASE = os.getenv("API_BASE", "http://api:8080")
UI_PORT = int(os.getenv("UI_PORT", "8081"))
BEHIND_PROXY = os.getenv("BEHIND_PROXY", "false").lower() == "true"

def get_api_base():
    """Get API base URL based on environment"""
    if BEHIND_PROXY:
        return "http://nginx/api"
    return API_BASE

class NDSpectraUI:
    """Main UI class for N-Dimensional Spectra visualization"""
    
    def __init__(self):
        self.user_id = ""
        self.notes = ""
        self.passes = 3
        self.responses = {}
        self.survey_data = {}
        self.result = None
        self.runs_data = []
        self.stats_data = {}
        self.selected_runs = set()
        self.filters = {
            "user_ids": [],
            "survey_id": None,
            "date_range": None,
            "selection_run_ids": []
        }
        
        # State for different views
        self.dashboard_data = {}
        self.history_data = {}
        self.compare_data = {}
        self.embeddings_data = {}
        
    def create_ui(self):
        """Create the main UI with tabs"""
        ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">')
        
        with ui.card().classes("w-full max-w-7xl mx-auto p-6"):
            ui.html('<h1 class="text-3xl font-bold text-gray-900 mb-6">N-Dimensional Spectra Explorer</h1>')
            
            # Configuration section
            self.create_config_section()
            
            # Main tabs
            with ui.tabs().classes('w-full') as tabs:
                survey_tab = ui.tab('Survey', icon='quiz')
                dashboard_tab = ui.tab('Dashboard', icon='dashboard')
                history_tab = ui.tab('History', icon='history')
                compare_tab = ui.tab('Compare', icon='compare')
                embeddings_tab = ui.tab('Embeddings', icon='scatter_plot')
                diagnostics_tab = ui.tab('Diagnostics', icon='analytics')
            
            with ui.tab_panels(tabs, value=survey_tab).classes('w-full'):
                # Survey Tab
                with ui.tab_panel(survey_tab):
                    self.create_survey_tab()
                
                # Dashboard Tab
                with ui.tab_panel(dashboard_tab):
                    self.create_dashboard_tab()
                
                # History Tab
                with ui.tab_panel(history_tab):
                    self.create_history_tab()
                
                # Compare Tab
                with ui.tab_panel(compare_tab):
                    self.create_compare_tab()
                
                # Embeddings Tab
                with ui.tab_panel(embeddings_tab):
                    self.create_embeddings_tab()
                
                # Diagnostics Tab
                with ui.tab_panel(diagnostics_tab):
                    self.create_diagnostics_tab()
    
    def create_config_section(self):
        """Create configuration section"""
        with ui.card().classes("w-full mb-6"):
            ui.html('<h2 class="text-xl font-semibold mb-4">Configuration</h2>')
            
            with ui.row().classes("w-full gap-4"):
                with ui.column().classes("flex-1"):
                    ui.input(label="User ID", placeholder="Enter user ID", on_change=self.on_user_id_change).classes("w-full")
                
                with ui.column().classes("flex-1"):
                    ui.input(label="Notes", placeholder="Optional notes", on_change=self.on_notes_change).classes("w-full")
                
                with ui.column().classes("flex-1"):
                    ui.number(label="Passes", value=3, min=1, max=10, on_change=self.on_passes_change).classes("w-full")
    
    def create_survey_tab(self):
        """Create survey tab with Likert sliders"""
        with ui.column().classes("w-full gap-4"):
            # Survey content
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Survey Questions</h3>')
                
                if not self.survey_data:
                    ui.label("Loading survey...").classes("text-gray-500")
                    self.load_survey()
                else:
                    self.render_survey_items()
            
            # Submit button
            with ui.row().classes("w-full justify-center"):
                ui.button("Run Survey Analysis", on_click=self.submit_survey).classes("bg-blue-500 text-white px-8 py-3")
            
            # Results display
            if self.result:
                self.display_survey_results()
    
    def create_dashboard_tab(self):
        """Create dashboard with 3D PAD scatter and other visualizations"""
        with ui.column().classes("w-full gap-6"):
            # Stats cards
            self.create_stats_cards()
            
            # 3D PAD Scatter
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">3D PAD Space</h3>')
                self.pad_3d_plot = ui.plotly({}).classes("w-full h-96")
            
            # 2D PAD with Density
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">2D PAD with Density</h3>')
                self.pad_2d_plot = ui.plotly({}).classes("w-full h-80")
            
            # Radar chart
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Trait Radar</h3>')
                self.radar_plot = ui.plotly({}).classes("w-full h-80")
            
            # Load dashboard data
            self.load_dashboard_data()
    
    def create_history_tab(self):
        """Create history tab with time series and trajectory plots"""
        with ui.column().classes("w-full gap-6"):
            # Time series
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Stability Over Time</h3>')
                self.stability_plot = ui.plotly({}).classes("w-full h-80")
            
            # Trajectory plot
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">PAD Trajectory</h3>')
                self.trajectory_plot = ui.plotly({}).classes("w-full h-80")
            
            # Runs table
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Run History</h3>')
                self.runs_table = ui.aggrid({
                    'columnDefs': [
                        {'headerName': 'Date', 'field': 'created_at'},
                        {'headerName': 'User', 'field': 'user_id'},
                        {'headerName': 'Stability', 'field': 'stability'},
                        {'headerName': '2D X', 'field': 'coords2d_x'},
                        {'headerName': '2D Y', 'field': 'coords2d_y'},
                    ],
                    'rowData': []
                }).classes("w-full h-64")
            
            # Load history data
            self.load_history_data()
    
    def create_compare_tab(self):
        """Create compare tab for multi-user analysis"""
        with ui.column().classes("w-full gap-6"):
            # User selection
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">User Selection</h3>')
                with ui.row().classes("w-full gap-4"):
                    ui.input(label="User IDs", placeholder="alice,bob,charlie", on_change=self.on_compare_users_change).classes("flex-1")
                    ui.button("Compare", on_click=self.load_compare_data).classes("bg-green-500 text-white")
            
            # 2D comparison scatter
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">2D Comparison</h3>')
                self.compare_2d_plot = ui.plotly({}).classes("w-full h-80")
            
            # 3D comparison scatter
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">3D Comparison</h3>')
                self.compare_3d_plot = ui.plotly({}).classes("w-full h-80")
            
            # Parallel coordinates
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Parallel Coordinates</h3>')
                self.parallel_plot = ui.plotly({}).classes("w-full h-80")
    
    def create_embeddings_tab(self):
        """Create embeddings tab for projection visualizations"""
        with ui.column().classes("w-full gap-6"):
            # Projection controls
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Projection Settings</h3>')
                with ui.row().classes("w-full gap-4"):
                    ui.select(label="Technique", options=["pca", "tsne"], value="pca", on_change=self.on_technique_change).classes("flex-1")
                    ui.select(label="Dimensions", options=[2, 3], value=2, on_change=self.on_dims_change).classes("flex-1")
                    ui.button("Generate Projection", on_click=self.generate_projection).classes("bg-purple-500 text-white")
            
            # Projection plot
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Projection Visualization</h3>')
                self.projection_plot = ui.plotly({}).classes("w-full h-96")
            
            # Explained variance (for PCA)
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Explained Variance</h3>')
                self.variance_plot = ui.plotly({}).classes("w-full h-64")
    
    def create_diagnostics_tab(self):
        """Create diagnostics tab with correlation and analysis plots"""
        with ui.column().classes("w-full gap-6"):
            # Correlation heatmap
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Trait Correlations</h3>')
                self.correlation_plot = ui.plotly({}).classes("w-full h-80")
            
            # Corner plot
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Trait Distributions</h3>')
                self.corner_plot = ui.plotly({}).classes("w-full h-96")
            
            # Outlier analysis
            with ui.card().classes("w-full"):
                ui.html('<h3 class="text-lg font-semibold mb-4">Outlier Analysis</h3>')
                self.outlier_plot = ui.plotly({}).classes("w-full h-80")
            
            # Load diagnostics data
            self.load_diagnostics_data()

    # Event handlers and data loading methods will be implemented next...
    
    # Event Handlers
    def on_user_id_change(self, e: ValueChangeEventArguments):
        """Handle user ID change"""
        self.user_id = e.value
    
    def on_notes_change(self, e: ValueChangeEventArguments):
        """Handle notes change"""
        self.notes = e.value
    
    def on_passes_change(self, e: ValueChangeEventArguments):
        """Handle passes change"""
        self.passes = int(e.value)
    
    def on_compare_users_change(self, e: ValueChangeEventArguments):
        """Handle compare users change"""
        if e.value:
            self.filters["user_ids"] = [uid.strip() for uid in e.value.split(",") if uid.strip()]
    
    def on_technique_change(self, e: ValueChangeEventArguments):
        """Handle projection technique change"""
        self.embeddings_data["technique"] = e.value
    
    def on_dims_change(self, e: ValueChangeEventArguments):
        """Handle projection dimensions change"""
        self.embeddings_data["dims"] = int(e.value)
    
    # Data Loading Methods
    def load_survey(self):
        """Load survey data from API"""
        try:
            response = requests.get(f"{get_api_base()}/survey", timeout=10)
            if response.status_code == 200:
                self.survey_data = response.json()
                # Initialize responses with default values
                self.responses = {item["id"]: 4 for item in self.survey_data.get("items", [])}
                print(f"Initialized {len(self.responses)} responses with default values")
                self.render_survey_items()
            else:
                ui.notify("Failed to load survey", type="error")
        except Exception as e:
            ui.notify(f"Failed to load survey: {str(e)}", type="error")
    
    def render_survey_items(self):
        """Render survey items with Likert sliders"""
        if not self.survey_data or "items" not in self.survey_data:
            return
        
        for item in self.survey_data["items"]:
            item_id = item["id"]
            with ui.card().classes("w-full mb-4"):
                with ui.row().classes("w-full items-center gap-4"):
                    with ui.column().classes("flex-1"):
                        ui.label(item["text"]).classes("text-sm font-medium")
                    
                    with ui.column().classes("flex-none"):
                        ui.label("1").classes("text-xs text-gray-500")
                    
                    with ui.column().classes("flex-1"):
                        slider = ui.slider(
                            min=1, max=7, value=4, step=1,
                            on_change=lambda e, id=item_id: self.update_response(id, e.value)
                        ).classes("w-full")
                    
                    with ui.column().classes("flex-none"):
                        ui.label("7").classes("text-xs text-gray-500")
    
    def update_response(self, item_id: str, value: int):
        """Update response for a survey item"""
        self.responses[item_id] = value
        print(f"Updated response for {item_id}: {value}")
    
    def submit_survey(self):
        """Submit survey responses to API with persistence"""
        if not self.user_id:
            ui.notify("Please enter a user ID", type="warning")
            return
        
        try:
            payload = {
                "user_id": self.user_id,
                "responses": self.responses,
                "passes": self.passes,
                "notes": self.notes
            }
            
            response = requests.post(
                f"{get_api_base()}/runs",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                self.result = response.json()
                ui.notify("Survey submitted successfully!", type="positive")
                # Refresh dashboard and history data
                self.load_dashboard_data()
                self.load_history_data()
            else:
                ui.notify(f"Failed to submit survey: {response.text}", type="error")
                
        except Exception as e:
            ui.notify(f"Error submitting survey: {str(e)}", type="error")
    
    def display_survey_results(self):
        """Display survey results"""
        if not self.result:
            return
        
        with ui.card().classes("w-full mt-4"):
            ui.html('<h3 class="text-lg font-semibold mb-4">Latest Results</h3>')
            
            # Create summary text
            summary = f"Run ID: {self.result.get('id', 'N/A')} | "
            summary += f"User: {self.result.get('user_id', 'N/A')} | "
            
            if 'coords2d_x' in self.result and 'coords2d_y' in self.result:
                summary += f"2D: ({self.result['coords2d_x']:.3f}, {self.result['coords2d_y']:.3f}) | "
            
            if 'stability' in self.result:
                summary += f"Stability: {self.result['stability']:.3f}"
            
            ui.label(summary).classes("text-sm text-gray-700")
    
    # Dashboard Methods
    def load_dashboard_data(self):
        """Load data for dashboard visualizations"""
        if not self.user_id:
            return
        
        try:
            # Load user's runs
            response = requests.get(
                f"{get_api_base()}/runs",
                params={"user_id": self.user_id, "page_size": 100},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.dashboard_data["runs"] = data.get("items", [])
                self.update_dashboard_plots()
            
            # Load stats
            stats_response = requests.get(
                f"{get_api_base()}/runs/stats",
                params={"user_id": self.user_id},
                timeout=10
            )
            
            if stats_response.status_code == 200:
                self.stats_data = stats_response.json()
                self.update_stats_cards()
                
        except Exception as e:
            print(f"Error loading dashboard data: {e}")
    
    def create_stats_cards(self):
        """Create statistics cards"""
        with ui.row().classes("w-full gap-4 mb-6"):
            self.total_runs_card = ui.card().classes("flex-1 p-4")
            self.avg_stability_card = ui.card().classes("flex-1 p-4")
            self.date_range_card = ui.card().classes("flex-1 p-4")
    
    def update_stats_cards(self):
        """Update statistics cards with data"""
        if not self.stats_data:
            return
        
        # Total runs
        with self.total_runs_card:
            ui.html('<div class="text-center">')
            ui.html(f'<div class="text-2xl font-bold text-blue-600">{self.stats_data.get("total_runs", 0)}</div>')
            ui.html('<div class="text-sm text-gray-600">Total Runs</div>')
            ui.html('</div>')
        
        # Average stability
        avg_stability = self.stats_data.get("mean_stability", 0)
        with self.avg_stability_card:
            ui.html('<div class="text-center">')
            ui.html(f'<div class="text-2xl font-bold text-green-600">{avg_stability:.3f}</div>')
            ui.html('<div class="text-sm text-gray-600">Avg Stability</div>')
            ui.html('</div>')
        
        # Date range
        date_range = self.stats_data.get("date_range", {})
        if date_range:
            start_date = datetime.fromisoformat(date_range["start"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            end_date = datetime.fromisoformat(date_range["end"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            
            with self.date_range_card:
                ui.html('<div class="text-center">')
                ui.html(f'<div class="text-lg font-semibold text-purple-600">{start_date}</div>')
                ui.html(f'<div class="text-sm text-gray-600">to {end_date}</div>')
                ui.html('</div>')
    
    def update_dashboard_plots(self):
        """Update dashboard plots with data"""
        if not self.dashboard_data.get("runs"):
            return
        
        runs = self.dashboard_data["runs"]
        
        # 3D PAD Scatter
        self.update_pad_3d_plot(runs)
        
        # 2D PAD with Density
        self.update_pad_2d_plot(runs)
        
        # Radar chart
        self.update_radar_plot(runs)
    
    def update_pad_3d_plot(self, runs):
        """Update 3D PAD scatter plot"""
        if not runs:
            return
        
        # Extract PAD coordinates
        x_coords = [run.get("coords3d_v", 0) for run in runs]
        y_coords = [run.get("coords3d_a", 0) for run in runs]
        z_coords = [run.get("coords3d_d", 0) for run in runs]
        dates = [run.get("created_at", "") for run in runs]
        
        fig = go.Figure(data=[go.Scatter3d(
            x=x_coords, y=y_coords, z=z_coords,
            mode='markers',
            marker=dict(
                size=8,
                color=[i for i in range(len(runs))],
                colorscale='Viridis',
                opacity=0.8
            ),
            text=dates,
            hovertemplate='<b>Date:</b> %{text}<br>' +
                         '<b>Valence:</b> %{x:.3f}<br>' +
                         '<b>Arousal:</b> %{y:.3f}<br>' +
                         '<b>Dominance:</b> %{z:.3f}<extra></extra>'
        )])
        
        fig.update_layout(
            title="3D PAD Space",
            scene=dict(
                xaxis_title="Valence",
                yaxis_title="Arousal", 
                zaxis_title="Dominance"
            ),
            height=400
        )
        
        self.pad_3d_plot.options = fig.to_dict()
    
    def update_pad_2d_plot(self, runs):
        """Update 2D PAD scatter with density"""
        if not runs:
            return
        
        # Extract 2D coordinates
        x_coords = [run.get("coords2d_x", 0) for run in runs]
        y_coords = [run.get("coords2d_y", 0) for run in runs]
        dates = [run.get("created_at", "") for run in runs]
        
        fig = go.Figure()
        
        # Add scatter plot
        fig.add_trace(go.Scatter(
            x=x_coords, y=y_coords,
            mode='markers',
            marker=dict(
                size=10,
                color=[i for i in range(len(runs))],
                colorscale='Viridis',
                opacity=0.7
            ),
            text=dates,
            hovertemplate='<b>Date:</b> %{text}<br>' +
                         '<b>X:</b> %{x:.3f}<br>' +
                         '<b>Y:</b> %{y:.3f}<extra></extra>',
            name="Runs"
        ))
        
        # Add density contour if enough points
        if len(runs) > 5:
            try:
                # Create density estimation
                x_range = np.linspace(min(x_coords), max(x_coords), 50)
                y_range = np.linspace(min(y_coords), max(y_coords), 50)
                X, Y = np.meshgrid(x_range, y_range)
                
                # Simple kernel density estimation
                positions = np.vstack([X.ravel(), Y.ravel()])
                values = np.vstack([x_coords, y_coords])
                kernel = gaussian_kde(values)
                Z = np.reshape(kernel(positions).T, X.shape)
                
                fig.add_trace(go.Contour(
                    x=x_range, y=y_range, z=Z,
                    colorscale='Blues',
                    opacity=0.3,
                    showscale=False,
                    name="Density"
                ))
            except:
                pass  # Skip density if calculation fails
        
        fig.update_layout(
            title="2D PAD with Density",
            xaxis_title="X",
            yaxis_title="Y",
            height=350
        )
        
        self.pad_2d_plot.options = fig.to_dict()
    
    def update_radar_plot(self, runs):
        """Update radar chart for traits"""
        if not runs or not runs[0].get("scores"):
            return
        
        # Get latest run scores
        latest_scores = runs[0]["scores"]
        traits = list(latest_scores.keys())
        values = list(latest_scores.values())
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=traits,
            fill='toself',
            name='Current Run'
        ))
        
        # Add cohort average if multiple runs
        if len(runs) > 1:
            avg_scores = {}
            for trait in traits:
                trait_values = [run.get("scores", {}).get(trait, 0) for run in runs if run.get("scores")]
                if trait_values:
                    avg_scores[trait] = np.mean(trait_values)
            
            if avg_scores:
                fig.add_trace(go.Scatterpolar(
                    r=list(avg_scores.values()),
                    theta=list(avg_scores.keys()),
                    fill='toself',
                    name='Cohort Average'
                ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[-1, 1]
                )),
            showlegend=True,
            title="Trait Radar Chart",
            height=350
        )
        
        self.radar_plot.options = fig.to_dict()
    
    # History Methods
    def load_history_data(self):
        """Load data for history visualizations"""
        if not self.user_id:
            return
        
        try:
            response = requests.get(
                f"{get_api_base()}/runs",
                params={"user_id": self.user_id, "page_size": 100},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.history_data["runs"] = data.get("items", [])
                self.update_history_plots()
                
        except Exception as e:
            print(f"Error loading history data: {e}")
    
    def update_history_plots(self):
        """Update history plots"""
        runs = self.history_data.get("runs", [])
        if not runs:
            return
        
        # Update stability plot
        self.update_stability_plot(runs)
        
        # Update trajectory plot
        self.update_trajectory_plot(runs)
        
        # Update runs table
        self.update_runs_table(runs)
    
    def update_stability_plot(self, runs):
        """Update stability time series plot"""
        if not runs:
            return
        
        # Sort by date
        runs_sorted = sorted(runs, key=lambda x: x.get("created_at", ""))
        
        dates = [run.get("created_at", "") for run in runs_sorted]
        stabilities = [run.get("stability", 0) for run in runs_sorted]
        
        # Convert dates to datetime
        try:
            date_objects = [datetime.fromisoformat(date.replace("Z", "+00:00")) for date in dates]
        except:
            date_objects = list(range(len(dates)))
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=date_objects,
            y=stabilities,
            mode='lines+markers',
            name='Stability',
            line=dict(color='blue', width=2),
            marker=dict(size=8, color='blue')
        ))
        
        fig.update_layout(
            title="Stability Over Time",
            xaxis_title="Date",
            yaxis_title="Stability",
            height=350
        )
        
        self.stability_plot.options = fig.to_dict()
    
    def update_trajectory_plot(self, runs):
        """Update PAD trajectory plot"""
        if not runs:
            return
        
        # Sort by date
        runs_sorted = sorted(runs, key=lambda x: x.get("created_at", ""))
        
        x_coords = [run.get("coords2d_x", 0) for run in runs_sorted]
        y_coords = [run.get("coords2d_y", 0) for run in runs_sorted]
        dates = [run.get("created_at", "") for run in runs_sorted]
        
        fig = go.Figure()
        
        # Add trajectory line
        fig.add_trace(go.Scatter(
            x=x_coords, y=y_coords,
            mode='lines+markers',
            name='Trajectory',
            line=dict(color='red', width=2),
            marker=dict(size=8, color='red')
        ))
        
        # Add arrows for direction
        for i in range(len(x_coords) - 1):
            fig.add_annotation(
                x=x_coords[i], y=y_coords[i],
                ax=x_coords[i+1], ay=y_coords[i+1],
                xref="x", yref="y",
                axref="x", ayref="y",
                text="", showarrow=True,
                arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="red"
            )
        
        fig.update_layout(
            title="PAD Trajectory",
            xaxis_title="X",
            yaxis_title="Y",
            height=350
        )
        
        self.trajectory_plot.options = fig.to_dict()
    
    def update_runs_table(self, runs):
        """Update runs table"""
        if not runs:
            return
        
        # Prepare table data
        table_data = []
        for run in runs:
            table_data.append({
                'created_at': run.get("created_at", "")[:10],  # Just date
                'user_id': run.get("user_id", ""),
                'stability': f"{run.get('stability', 0):.3f}",
                'coords2d_x': f"{run.get('coords2d_x', 0):.3f}",
                'coords2d_y': f"{run.get('coords2d_y', 0):.3f}"
            })
        
        self.runs_table.options['rowData'] = table_data
    
    # Compare Methods
    def load_compare_data(self):
        """Load comparison data"""
        if not self.filters["user_ids"]:
            ui.notify("Please select users to compare", type="warning")
            return
        
        try:
            user_ids_str = ",".join(self.filters["user_ids"])
            response = requests.get(
                f"{get_api_base()}/compare",
                params={"user_ids": user_ids_str, "limit_per_user": 50},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.compare_data = data.get("results", {})
                self.update_compare_plots()
            else:
                ui.notify("Failed to load comparison data", type="error")
                
        except Exception as e:
            ui.notify(f"Error loading comparison data: {str(e)}", type="error")
    
    def update_compare_plots(self):
        """Update comparison plots"""
        if not self.compare_data:
            return
        
        # Update 2D comparison
        self.update_compare_2d_plot()
        
        # Update 3D comparison
        self.update_compare_3d_plot()
        
        # Update parallel coordinates
        self.update_parallel_plot()
    
    def update_compare_2d_plot(self):
        """Update 2D comparison scatter"""
        if not self.compare_data:
            return
        
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        for i, (user_id, runs) in enumerate(self.compare_data.items()):
            if not runs:
                continue
            
            x_coords = [run.get("coords2d_x", 0) for run in runs]
            y_coords = [run.get("coords2d_y", 0) for run in runs]
            
            fig.add_trace(go.Scatter(
                x=x_coords, y=y_coords,
                mode='markers',
                name=user_id,
                marker=dict(
                    size=8,
                    color=colors[i % len(colors)],
                    opacity=0.7
                )
            ))
        
        fig.update_layout(
            title="2D Comparison by User",
            xaxis_title="X",
            yaxis_title="Y",
            height=350
        )
        
        self.compare_2d_plot.options = fig.to_dict()
    
    def update_compare_3d_plot(self):
        """Update 3D comparison scatter"""
        if not self.compare_data:
            return
        
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        for i, (user_id, runs) in enumerate(self.compare_data.items()):
            if not runs:
                continue
            
            x_coords = [run.get("coords3d_v", 0) for run in runs]
            y_coords = [run.get("coords3d_a", 0) for run in runs]
            z_coords = [run.get("coords3d_d", 0) for run in runs]
            
            fig.add_trace(go.Scatter3d(
                x=x_coords, y=y_coords, z=z_coords,
                mode='markers',
                name=user_id,
                marker=dict(
                    size=6,
                    color=colors[i % len(colors)],
                    opacity=0.7
                )
            ))
        
        fig.update_layout(
            title="3D Comparison by User",
            scene=dict(
                xaxis_title="Valence",
                yaxis_title="Arousal",
                zaxis_title="Dominance"
            ),
            height=400
        )
        
        self.compare_3d_plot.options = fig.to_dict()
    
    def update_parallel_plot(self):
        """Update parallel coordinates plot"""
        if not self.compare_data:
            return
        
        # Prepare data for parallel coordinates
        all_data = []
        for user_id, runs in self.compare_data.items():
            for run in runs:
                if run.get("scores"):
                    data_point = {"user_id": user_id}
                    data_point.update(run["scores"])
                    all_data.append(data_point)
        
        if not all_data:
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        # Create parallel coordinates plot
        fig = go.Figure(data=
            go.Parcoords(
                line=dict(
                    color=df['user_id'].astype('category').cat.codes,
                    colorscale='Set1'
                ),
                dimensions=[
                    dict(range=[df[col].min(), df[col].max()],
                         label=col, values=df[col])
                    for col in df.columns if col != 'user_id'
                ]
            )
        )
        
        fig.update_layout(
            title="Parallel Coordinates by User",
            height=350
        )
        
        self.parallel_plot.options = fig.to_dict()
    
    # Embeddings Methods
    def generate_projection(self):
        """Generate projection visualization"""
        try:
            payload = {
                "technique": self.embeddings_data.get("technique", "pca"),
                "dims": self.embeddings_data.get("dims", 2),
                "user_ids": self.filters["user_ids"] if self.filters["user_ids"] else None,
                "limit_per_user": 100
            }
            
            response = requests.post(
                f"{get_api_base()}/viz/project",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.embeddings_data["projection"] = data
                self.update_projection_plots()
            else:
                ui.notify("Failed to generate projection", type="error")
                
        except Exception as e:
            ui.notify(f"Error generating projection: {str(e)}", type="error")
    
    def update_projection_plots(self):
        """Update projection plots"""
        projection = self.embeddings_data.get("projection")
        if not projection:
            return
        
        # Update main projection plot
        self.update_projection_plot(projection)
        
        # Update explained variance plot (for PCA)
        if projection.get("explained_variance"):
            self.update_variance_plot(projection["explained_variance"])
    
    def update_projection_plot(self, projection):
        """Update main projection plot"""
        points = projection.get("points", [])
        if not points:
            return
        
        dims = projection.get("dims", 2)
        technique = projection.get("technique", "pca")
        
        if dims == 2:
            x_coords = [point["x"] for point in points]
            y_coords = [point["y"] for point in points]
            user_ids = [point["user_id"] for point in points]
            
            fig = go.Figure()
            
            # Color by user
            unique_users = list(set(user_ids))
            colors = px.colors.qualitative.Set1
            
            for i, user_id in enumerate(unique_users):
                user_points = [j for j, uid in enumerate(user_ids) if uid == user_id]
                user_x = [x_coords[j] for j in user_points]
                user_y = [y_coords[j] for j in user_points]
                
                fig.add_trace(go.Scatter(
                    x=user_x, y=user_y,
                    mode='markers',
                    name=user_id,
                    marker=dict(
                        size=8,
                        color=colors[i % len(colors)],
                        opacity=0.7
                    )
                ))
            
            fig.update_layout(
                title=f"{technique.upper()} Projection (2D)",
                xaxis_title="Component 1",
                yaxis_title="Component 2",
                height=400
            )
            
        else:  # 3D
            x_coords = [point["x"] for point in points]
            y_coords = [point["y"] for point in points]
            z_coords = [point["z"] for point in points]
            user_ids = [point["user_id"] for point in points]
            
            fig = go.Figure()
            
            # Color by user
            unique_users = list(set(user_ids))
            colors = px.colors.qualitative.Set1
            
            for i, user_id in enumerate(unique_users):
                user_points = [j for j, uid in enumerate(user_ids) if uid == user_id]
                user_x = [x_coords[j] for j in user_points]
                user_y = [y_coords[j] for j in user_points]
                user_z = [z_coords[j] for j in user_points]
                
                fig.add_trace(go.Scatter3d(
                    x=user_x, y=user_y, z=user_z,
                    mode='markers',
                    name=user_id,
                    marker=dict(
                        size=6,
                        color=colors[i % len(colors)],
                        opacity=0.7
                    )
                ))
            
            fig.update_layout(
                title=f"{technique.upper()} Projection (3D)",
                scene=dict(
                    xaxis_title="Component 1",
                    yaxis_title="Component 2",
                    zaxis_title="Component 3"
                ),
                height=400
            )
        
        self.projection_plot.options = fig.to_dict()
    
    def update_variance_plot(self, explained_variance):
        """Update explained variance plot"""
        if not explained_variance:
            return
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=[f"PC{i+1}" for i in range(len(explained_variance))],
            y=explained_variance,
            marker_color='lightblue'
        ))
        
        fig.update_layout(
            title="Explained Variance",
            xaxis_title="Principal Components",
            yaxis_title="Explained Variance Ratio",
            height=300
        )
        
        self.variance_plot.options = fig.to_dict()
    
    # Diagnostics Methods
    def load_diagnostics_data(self):
        """Load data for diagnostics visualizations"""
        try:
            # Load all runs for analysis
            response = requests.get(
                f"{get_api_base()}/runs",
                params={"page_size": 1000},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                runs = data.get("items", [])
                
                if runs:
                    self.update_diagnostics_plots(runs)
                    
        except Exception as e:
            print(f"Error loading diagnostics data: {e}")
    
    def update_diagnostics_plots(self, runs):
        """Update diagnostics plots"""
        if not runs:
            return
        
        # Update correlation plot
        self.update_correlation_plot(runs)
        
        # Update corner plot
        self.update_corner_plot(runs)
        
        # Update outlier plot
        self.update_outlier_plot(runs)
    
    def update_correlation_plot(self, runs):
        """Update correlation heatmap"""
        if not runs or not runs[0].get("scores"):
            return
        
        # Extract scores for correlation analysis
        scores_data = []
        for run in runs:
            if run.get("scores"):
                scores_data.append(run["scores"])
        
        if len(scores_data) < 2:
            return
        
        # Create correlation matrix
        df = pd.DataFrame(scores_data)
        corr_matrix = df.corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0
        ))
        
        fig.update_layout(
            title="Trait Correlations",
            height=350
        )
        
        self.correlation_plot.options = fig.to_dict()
    
    def update_corner_plot(self, runs):
        """Update corner plot for trait distributions"""
        if not runs or not runs[0].get("scores"):
            return
        
        # Extract scores
        scores_data = []
        for run in runs:
            if run.get("scores"):
                scores_data.append(run["scores"])
        
        if len(scores_data) < 2:
            return
        
        df = pd.DataFrame(scores_data)
        
        # Select top traits for visualization
        top_traits = df.columns[:6].tolist()  # Limit to 6 traits for readability
        
        # Create subplots
        fig = make_subplots(
            rows=len(top_traits), cols=len(top_traits),
            subplot_titles=top_traits,
            shared_xaxes=True, shared_yaxes=True
        )
        
        for i, trait1 in enumerate(top_traits, 1):
            for j, trait2 in enumerate(top_traits, 1):
                if i == j:
                    # Histogram on diagonal
                    fig.add_trace(
                        go.Histogram(x=df[trait1], name=trait1, showlegend=False),
                        row=i, col=j
                    )
                else:
                    # Scatter plot off diagonal
                    fig.add_trace(
                        go.Scatter(
                            x=df[trait1], y=df[trait2],
                            mode='markers',
                            marker=dict(size=4, opacity=0.6),
                            showlegend=False
                        ),
                        row=i, col=j
                    )
        
        fig.update_layout(
            title="Trait Distributions and Relationships",
            height=500,
            showlegend=False
        )
        
        self.corner_plot.options = fig.to_dict()
    
    def update_outlier_plot(self, runs):
        """Update outlier analysis plot"""
        if not runs:
            return
        
        # Extract stability values
        stabilities = [run.get("stability", 0) for run in runs if run.get("stability") is not None]
        
        if len(stabilities) < 2:
            return
        
        # Calculate statistics
        mean_stability = np.mean(stabilities)
        std_stability = np.std(stabilities)
        
        # Identify outliers (beyond 2 standard deviations)
        outliers = [s for s in stabilities if abs(s - mean_stability) > 2 * std_stability]
        normal = [s for s in stabilities if abs(s - mean_stability) <= 2 * std_stability]
        
        fig = go.Figure()
        
        # Add normal points
        fig.add_trace(go.Scatter(
            x=list(range(len(normal))),
            y=normal,
            mode='markers',
            name='Normal',
            marker=dict(color='blue', size=8)
        ))
        
        # Add outliers
        if outliers:
            outlier_indices = [i for i, s in enumerate(stabilities) if abs(s - mean_stability) > 2 * std_stability]
            fig.add_trace(go.Scatter(
                x=outlier_indices,
                y=outliers,
                mode='markers',
                name='Outliers',
                marker=dict(color='red', size=12, symbol='x')
            ))
        
        # Add mean line
        fig.add_hline(y=mean_stability, line_dash="dash", line_color="gray", annotation_text="Mean")
        
        fig.update_layout(
            title="Stability Outlier Analysis",
            xaxis_title="Run Index",
            yaxis_title="Stability",
            height=350
        )
        
        self.outlier_plot.options = fig.to_dict()

# Initialize UI
nd_ui = NDSpectraUI()

def main():
    """Main application entry point"""
    nd_ui.create_ui()
    ui.run(
        host="0.0.0.0",
        port=UI_PORT,
        reload=False,  # Disable reloader in Docker
        show=False
    )

if __name__ == "__main__":
    main() 