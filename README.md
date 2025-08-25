# N-Dimensional Spectra Explorer

A comprehensive visualization platform for exploring multidimensional psychological spectra through interactive surveys, advanced analytics, and projection techniques.

## 🏗️ Architecture

```
[Browser] → NGINX :80
    ├─ /api/* → FastAPI (api:8080)
    └─ / → NiceGUI (ui:8081)
```

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and setup
git clone <repository>
cd ndimensionalspectra

# Start all services
docker compose up -d

# Access the application
open http://localhost/
```

### Manual Docker Run

```bash
# Build images
docker buildx bake

# Run services individually
docker run -d --name api ndimensionalspectra-api:latest
docker run -d --name ui -e API_BASE=http://nginx/api ndimensionalspectra-ui:latest
docker run -d --name nginx -p 80:80 --link api --link ui ndimensionalspectra-nginx:latest
```

## 📊 Features

### 🎯 Survey Interface
- **Interactive Likert Scales**: 1-7 rating sliders for each survey item
- **Real-time Response Tracking**: Automatic saving of responses as you move sliders
- **User Configuration**: Set user ID, notes, and number of passes
- **Instant Results**: View placement coordinates and stability scores immediately

### 📈 Dashboard Visualizations
- **3D PAD Space**: Interactive 3D scatter plot of Valence, Arousal, and Dominance
- **2D PAD with Density**: 2D scatter with kernel density estimation contours
- **Trait Radar Charts**: Spider/radar plots comparing current run vs cohort averages
- **Statistics Cards**: Total runs, average stability, and date range summaries

### 📚 History Analysis
- **Stability Time Series**: Line charts showing stability trends over time
- **PAD Trajectory**: 2D path visualization with directional arrows
- **Run History Table**: Sortable table with export capabilities
- **Interactive Filtering**: Date ranges and user-specific views

### 🔍 Multi-User Comparison
- **2D Comparison Scatter**: Color-coded points by user
- **3D Comparison Scatter**: 3D visualization with user legends
- **Parallel Coordinates**: Multi-dimensional trait comparison across users
- **Dynamic User Selection**: Comma-separated user ID input

### 🧠 Advanced Embeddings
- **PCA Projections**: Principal Component Analysis for dimensionality reduction
- **t-SNE Visualizations**: t-Distributed Stochastic Neighbor Embedding
- **2D/3D Support**: Toggle between 2D and 3D projection views
- **Explained Variance**: Bar charts showing PCA component importance
- **Interactive Controls**: Technique selection and dimension toggles

### 🔬 Diagnostic Analytics
- **Correlation Heatmaps**: Trait correlation matrices with color coding
- **Corner Plots**: Pairwise trait distributions and relationships
- **Outlier Analysis**: Statistical outlier detection and visualization
- **Comprehensive Statistics**: Full dataset analysis and insights

## 🛠️ API Endpoints

### Core Endpoints
- `GET /api/health` - Health check
- `GET /api/survey` - Get survey questions
- `POST /api/run` - Legacy run endpoint (optional persistence)
- `POST /api/runs` - Create persistent run
- `GET /api/runs` - List runs with filtering and pagination
- `GET /api/runs/{id}` - Get specific run
- `GET /api/runs/stats` - Get run statistics and aggregates

### Comparison & Analysis
- `GET /api/compare` - Compare runs across multiple users
- `POST /api/viz/project` - Generate projection visualizations

### Projection Parameters
```json
{
  "technique": "pca|tsne",
  "dims": 2|3,
  "user_ids": ["user1", "user2"],
  "survey_id": "optional",
  "since": "2025-01-01T00:00:00Z",
  "until": "2025-12-31T23:59:59Z",
  "features": ["valence", "arousal", "dominance"],
  "limit_per_user": 100
}
```

## 🗄️ Database

### Persistence Options
- **PostgreSQL**: Primary database (when `DATABASE_URL` is set)
- **SQLite**: Fallback database (`./data/om.db`)

### Schema
```sql
runs (
  id UUID PRIMARY KEY,
  user_id TEXT,
  survey_id TEXT,
  passes INTEGER,
  created_at TIMESTAMP,
  coords2d_x REAL,
  coords2d_y REAL,
  coords3d_v REAL,
  coords3d_a REAL,
  coords3d_d REAL,
  stability REAL,
  scores JSONB,
  final_state JSONB,
  notes TEXT
)
```

## 🔧 Configuration

### Environment Variables
- `API_BASE`: API base URL (default: `http://api:8080`)
- `UI_PORT`: UI port (default: `8081`)
- `DATABASE_URL`: PostgreSQL connection string
- `BEHIND_PROXY`: Set to `true` when behind NGINX

### Docker Compose Services
- **api**: FastAPI backend with PostgreSQL/SQLite
- **ui**: NiceGUI frontend with visualization components
- **nginx**: Reverse proxy with WebSocket support
- **db**: PostgreSQL database (optional)

## 📦 Dependencies

### Core
- **FastAPI**: Modern web framework for APIs
- **NiceGUI**: Interactive web UI framework
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation

### Visualization
- **Plotly**: Interactive plotting library
- **Pandas**: Data manipulation
- **NumPy**: Numerical computing
- **SciPy**: Scientific computing

### Machine Learning
- **scikit-learn**: PCA and t-SNE implementations
- **Kernel Density Estimation**: For density contours

## 🚀 Development

### Local Development
```bash
# Install dependencies
uv sync

# Run API
uvicorn src.ndimensionalspectra.ontogenic_api:app --reload

# Run UI
python -m src.ndimensionalspectra.nicegui_app
```

### Building Images
```bash
# Build all images
docker buildx bake

# Build specific target
docker buildx bake api
docker buildx bake ui
docker buildx bake nginx

# Push to registry
docker buildx bake push
```

## 🧪 Testing

### Acceptance Tests
```bash
# Health check
curl -s http://localhost/api/health

# Survey loading
curl -s http://localhost/api/survey | jq .

# Projection test
curl -s -X POST http://localhost/api/viz/project \
  -H 'Content-Type: application/json' \
  -d '{"technique":"pca","dims":2}' | jq .

# UI accessibility
curl -s http://localhost/ | grep -q "NiceGUI"
```

## 📈 Performance

### Optimization Features
- **Server-side Caching**: Projection results cached by parameters
- **Pagination**: Large datasets handled efficiently
- **Downsampling**: Automatic point reduction for large visualizations
- **Lazy Loading**: Visualizations load on demand

### Scaling Considerations
- **Database Indexing**: Optimized queries with proper indexes
- **Connection Pooling**: Efficient database connections
- **WebSocket Stability**: Reliable real-time updates
- **Memory Management**: Efficient handling of large datasets

## 🔒 Security

### Features
- **Input Validation**: All inputs validated with Pydantic
- **SQL Injection Protection**: Parameterized queries
- **Rate Limiting**: API endpoint protection
- **CORS Configuration**: Proper cross-origin handling

### Best Practices
- **Non-root Containers**: All services run as non-root users
- **Health Checks**: Comprehensive health monitoring
- **Environment Isolation**: Proper secret management
- **Network Security**: Isolated Docker networks

## 📝 Usage Examples

### Basic Survey Flow
1. Open `http://localhost/`
2. Enter User ID in configuration
3. Complete survey using Likert sliders
4. Click "Run Survey Analysis"
5. View results in Dashboard tab

### Multi-User Comparison
1. Navigate to Compare tab
2. Enter user IDs: `alice,bob,charlie`
3. Click "Compare"
4. Explore 2D/3D scatter plots
5. Analyze parallel coordinates

### Advanced Analytics
1. Go to Embeddings tab
2. Select technique (PCA/t-SNE)
3. Choose dimensions (2D/3D)
4. Click "Generate Projection"
5. Explore explained variance

### Diagnostic Analysis
1. Visit Diagnostics tab
2. View correlation heatmaps
3. Analyze trait distributions
4. Identify statistical outliers
5. Export insights

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

### Code Standards
- **Type Hints**: Full type annotation
- **Documentation**: Comprehensive docstrings
- **Testing**: Unit and integration tests
- **Linting**: Black, isort, flake8

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **NiceGUI**: Modern Python web framework
- **Plotly**: Interactive visualization library
- **scikit-learn**: Machine learning toolkit
- **FastAPI**: High-performance web framework
