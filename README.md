# GitHub Repository Analyzer

A generic GitHub repository analyzer using **LangGraph agents** + **GitHub MCP** + **Azure OpenAI**.

## Features

### 🔍 Repository Explorer Agent
- **Dynamically discovers** repository structure
- **No hardcoded service names** - adapts to any repository
- Identifies services, apps, and libraries automatically
- Extracts technology stack, dependencies, and architecture
- Maps service connections and communication patterns

### 🐛 Issues Analyzer Agent  
- Analyzes GitHub issues and pull requests
- Categorizes: bugs, features, enhancements, docs, questions
- Extracts metadata: code owners, contributors, affected services
- Identifies patterns and pain points

### 🤖 LangGraph Workflow
- Orchestrates agents in a coordinated workflow
- Parallel agent execution where possible
- State management across analysis steps

### 📊 Structured Output
- JSON format ready for knowledge graphs
- Service topology and connections
- Issues metadata and categorization
- Technology patterns and commonalities

## Setup

### Prerequisites
- Python 3.11+
- Node.js (for GitHub MCP server via npx)
- Azure OpenAI API access
- GitHub Personal Access Token

### Installation

```powershell
cd c:\SE\github-analyzer

# Activate virtual environment
..\eshop-ontology-poc\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env.template` to `.env` and configure:

```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# GitHub
GITHUB_TOKEN=your-github-token

# Target Repository (change for any repo!)
GITHUB_REPO_OWNER=dotnet
GITHUB_REPO_NAME=eShop
```

## Usage

### Analyze Any Repository

Simply change the `.env` configuration:

```env
GITHUB_REPO_OWNER=microsoft
GITHUB_REPO_NAME=semantic-kernel
```

Then run:

```powershell
python main.py
```

### Output

Results saved to `output/{owner}_{repo}_{timestamp}.json`:

```json
{
  "analysis_metadata": {
    "analyzed_at": "2025-01-XX...",
    "repository": {"owner": "...", "name": "..."}
  },
  "repository": {
    "services": [...],
    "connections": [...],
    "patterns": {...},
    "tech_stack": [...]
  },
  "issues": {
    "categorized_issues": {...},
    "metadata": {...},
    "patterns": {...}
  }
}
```


## Examples

### Analyze dotnet/eShop
```env
GITHUB_REPO_OWNER=dotnet
GITHUB_REPO_NAME=eShop
```

### Analyze microsoft/semantic-kernel
```env
GITHUB_REPO_OWNER=microsoft
GITHUB_REPO_NAME=semantic-kernel
```

### Analyze any public repository
```env
GITHUB_REPO_OWNER=owner-name
GITHUB_REPO_NAME=repo-name
```

## License

MIT
