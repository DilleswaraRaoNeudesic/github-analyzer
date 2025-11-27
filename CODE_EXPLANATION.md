# GitHub Analyzer - Code Explanation

## Project Overview
A generic GitHub repository analyzer using LangGraph agents, GitHub MCP, and Azure OpenAI to automatically discover services, analyze issues, and extract structured metadata from any repository.

---

## File Structure and Explanations

### 📁 `main.py` - Application Entry Point & LangGraph Workflow

**Purpose**: Orchestrates the entire analysis workflow using LangGraph state machine.

**Key Components**:

```python
class AnalysisState(TypedDict):
    """State passed between agents"""
    repository: dict              # Target repo info
    repository_analysis: dict      # Services, connections, patterns
    issues_analysis: dict         # Issues, PRs, metadata
    final_output: dict            # Combined results
    status: str                   # Workflow status
```

**Workflow**:
1. **Initialize**: Load config from .env, setup Azure OpenAI client
2. **Create GitHub MCP connection**: Context manager for MCP tools
3. **Build LangGraph workflow**:
   - Node 1: `explore_repository` - Calls RepositoryExplorerAgent
   - Node 2: `analyze_issues` - Calls IssuesAnalyzerAgent  
   - Node 3: `combine_results` - Merges outputs
   - Flow: explore_repo → analyze_issues → combine → END

**Key Code**:
```python
class GitHubAnalyzer:
    def __init__(self):
        # Load configuration from .env
        self.owner = os.getenv("GITHUB_REPO_OWNER")
        self.repo = os.getenv("GITHUB_REPO_NAME")
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        # Initialize Azure OpenAI
        self.llm = AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            temperature=0.1
        )
    
    async def analyze(self):
        # Create MCP connection
        async with GitHubMCPTools(self.github_token) as github_tools:
            # Initialize agents
            repo_explorer = RepositoryExplorerAgent(self.llm, github_tools)
            issues_analyzer = IssuesAnalyzerAgent(self.llm, github_tools)
            
            # Build LangGraph state machine
            workflow = StateGraph(AnalysisState)
            workflow.add_node("explore_repo", explore_repository)
            workflow.add_node("analyze_issues", analyze_issues)
            workflow.add_node("combine", combine_results)
            
            # Define flow
            workflow.set_entry_point("explore_repo")
            workflow.add_edge("explore_repo", "analyze_issues")
            workflow.add_edge("analyze_issues", "combine")
            workflow.add_edge("combine", END)
            
            # Execute workflow
            app = workflow.compile()
            final_state = await app.ainvoke(initial_state)
            
            # Save output
            self._save_output(final_state["final_output"])
```

**Output**: Saves JSON file to `output/{owner}_{repo}_{timestamp}.json`

---

### 📁 `tools/github_mcp.py` - GitHub MCP Tools Wrapper

**Purpose**: Clean interface to GitHub MCP server, abstracts all GitHub API interactions.

**Key Methods**:

```python
class GitHubMCPTools:
    """Wrapper for GitHub MCP server tools"""
    
    async def __aenter__(self):
        """Connect to MCP server via npx"""
        # Starts: npx -y @modelcontextprotocol/server-github
        # Uses GITHUB_PERSONAL_ACCESS_TOKEN for authentication
        
    async def get_file_contents(self, owner, repo, path, silent=False):
        """
        Get file or directory contents
        - For files: returns file content as string
        - For directories: returns JSON array of items
        - silent=True: suppress 404 errors
        """
        result = await self.session.call_tool(
            "get_file_contents",
            arguments={"owner": owner, "repo": repo, "path": path}
        )
        
    async def list_issues(self, owner, repo, state="open", per_page=30):
        """
        List repository issues
        - state: "open", "closed", "all"
        - Returns: JSON array of issue objects
        """
        
    async def get_issue(self, owner, repo, issue_number):
        """Get details of specific issue by number"""
        
    async def search_code(self, owner, repo, query, per_page=10):
        """
        Search code in repository
        - query: search term
        - Automatically adds repo qualifier
        - Returns: Search results with file paths
        """
        search_query = f"{query} repo:{owner}/{repo}"
        
    async def list_pull_requests(self, owner, repo, state="open"):
        """List pull requests"""
```

**MCP Connection Flow**:
1. Spawns `npx` process running GitHub MCP server
2. Communicates via stdio (stdin/stdout)
3. Uses MCP protocol to call tools
4. Returns results as structured data

**Error Handling**: 
- Silently handles 404s when `silent=True`
- Prints other errors for debugging
- Returns `None` on failure

---

### 📁 `agents/repository_explorer.py` - Repository Analysis Agent

**Purpose**: Discovers repository structure, identifies services dynamically, analyzes architecture.

**Workflow**:

```python
class RepositoryExplorerAgent:
    async def explore(self):
        """Main exploration workflow"""
        
        # Step 1: Get README
        readme = await self.github.get_file_contents(owner, repo, "README.md")
        
        # Step 2: Explore src/ directory
        src_structure = await self.github.get_file_contents(owner, repo, "src")
        directories = self._parse_directory_structure(src_structure)
        
        # Step 3: Search for project files
        csproj_results = await self.github.search_code(
            owner, repo, "extension:csproj", per_page=30
        )
        
        # Step 4: Identify services using LLM
        services = await self._identify_services(readme, directories, project_files)
        
        # Step 5: Get detailed info for each service
        detailed_services = await self._get_service_details(services)
        
        # Step 6: Analyze connections and patterns
        analysis = await self._analyze_architecture(readme, detailed_services)
```

**Key Methods**:

```python
async def _identify_services(self, readme, directories, project_files):
    """
    Use LLM to identify services from repository structure
    
    Input: README, directory list, project files
    Output: List of service names
    
    LLM Prompt:
    - Analyze README and directory structure
    - Look for API services, web apps, background services, libraries
    - Return JSON array: ["Service1", "Service2", ...]
    """
    prompt = f"""
    Based on README and structure, identify ALL services/applications.
    Look for: API services, Web apps, Background services, Libraries
    
    README: {readme[:3000]}
    Directories: {directories}
    Project files: {project_files}
    
    Return JSON array of service names.
    """
    response = await self.llm.ainvoke([SystemMessage(...), HumanMessage(prompt)])

async def _get_service_details(self, services):
    """
    For each service, fetch and analyze source files
    
    For each service:
    1. Try to get {service}.csproj
    2. Try to get Program.cs (only for executables)
    3. Analyze with LLM to extract metadata
    """
    for service in services:
        project_content = await self.github.get_file_contents(
            f"src/{service}/{service}.csproj", silent=True
        )
        
        # Only fetch Program.cs for APIs/apps
        if is_executable(service):
            program_cs = await self.github.get_file_contents(
                f"src/{service}/Program.cs", silent=True
            )

async def _analyze_service(self, service_name, project_file, program_cs):
    """
    Use LLM to extract service metadata
    
    Input: Service name, .csproj content, Program.cs content
    Output: JSON with service details
    
    Extracts:
    - name: Service name
    - description: What it does (concrete, specific)
    - technologies: [ASP.NET, gRPC, Redis, etc.]
    - dependencies: [other services, databases]
    - type: api|webapp|library|service
    - port: Port number if found
    """

async def _analyze_architecture(self, readme, services):
    """
    Analyze overall architecture and connections
    
    Input: README, list of services
    Output: Architecture analysis
    
    Returns:
    - overview: Repository description
    - connections: [{from, to, method}] - service communication
    - patterns: {shared_technologies, communication_styles}
    - tech_stack: Primary technologies used
    """
```

**Smart Features**:
- **Dynamic discovery**: No hardcoded service names
- **Selective fetching**: Only fetches Program.cs for executable projects
- **Silent 404s**: Doesn't spam errors for missing files
- **LLM-powered**: Uses AI to understand repository structure

---

### 📁 `agents/issues_analyzer.py` - Issues & PR Analysis Agent

**Purpose**: Analyzes GitHub issues, pull requests, and extracts metadata about development activity.

**Workflow**:

```python
class IssuesAnalyzerAgent:
    async def analyze(self):
        """Main issues analysis workflow"""
        
        # Step 1: Get open issues
        open_issues = await self.github.list_issues(owner, repo, state="open", per_page=50)
        
        # Step 2: Get closed issues
        closed_issues = await self.github.list_issues(owner, repo, state="closed", per_page=30)
        
        # Step 3: Get pull requests
        prs = await self.github.list_pull_requests(owner, repo, state="open", per_page=30)
        
        # Step 4: Categorize issues with LLM
        categorized = await self._categorize_issues(open_issues, closed_issues)
        
        # Step 5: Extract metadata
        metadata = await self._extract_metadata(open_issues, closed_issues, prs)
        
        # Step 6: Identify patterns
        patterns = await self._identify_patterns(categorized, metadata)
```

**Key Methods**:

```python
def _parse_issues(self, content):
    """
    Parse GitHub API JSON response to extract issue data
    
    Extracts:
    - number, title, state, labels
    - created_at, updated_at
    - user, assignees
    - comments count
    - body (first 500 chars)
    """
    return [{
        "number": issue["number"],
        "title": issue["title"],
        "labels": [label["name"] for label in issue["labels"]],
        "user": issue["user"]["login"],
        "assignees": [a["login"] for a in issue["assignees"]],
        ...
    }]

async def _categorize_issues(self, open_issues, closed_issues):
    """
    Use LLM to categorize issues
    
    Input: List of issues
    Output: Categorized by type
    
    Categories:
    - bugs: [{number, title, priority}]
    - features: [{number, title, status}]
    - enhancements, documentation, questions, other
    
    LLM analyzes title, labels, body to determine category
    Fallback: Use GitHub labels if LLM fails
    """

async def _extract_metadata(self, open_issues, closed_issues, prs):
    """
    Extract metadata from issues and PRs
    
    Extracts:
    - code_owners: Active maintainers
    - active_contributors: Frequent contributors
    - affected_services: Services mentioned in issues
    - common_technologies: Tech stack from issues
    - issue_labels: Label frequency distribution
    """

async def _identify_patterns(self, categorized, metadata):
    """
    Identify patterns in issues
    
    Analyzes:
    - common_bug_areas: Frequent bug locations
    - frequent_feature_requests: Most requested features
    - pain_points: Common user complaints
    - improvement_opportunities: Areas for improvement
    """
```

**Output Structure**:
```json
{
  "summary": {
    "total_open_issues": 50,
    "total_closed_issues": 30,
    "total_prs": 20
  },
  "categorized_issues": {
    "bugs": [...],
    "features": [...],
    "enhancements": [...]
  },
  "metadata": {
    "code_owners": ["user1", "user2"],
    "affected_services": ["ServiceA", "ServiceB"]
  },
  "patterns": {
    "common_bug_areas": ["area1", "area2"],
    "pain_points": [...]
  }
}
```

---

### 📁 `.env` - Configuration File

**Purpose**: Store all configuration - works with any repository by changing these values.

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# GitHub Configuration
GITHUB_TOKEN=ghp_your-github-token

# Target Repository (CHANGE THIS FOR ANY REPO)
GITHUB_REPO_OWNER=dotnet
GITHUB_REPO_NAME=eShop

# Analysis Settings
MAX_FILE_SIZE=100000
MAX_DIRECTORY_DEPTH=3
OUTPUT_DIR=output
```

**To analyze a different repository**, just change:
```env
GITHUB_REPO_OWNER=microsoft
GITHUB_REPO_NAME=semantic-kernel
```

---

### 📁 `requirements.txt` - Python Dependencies

```txt
langgraph>=0.2.45          # Agent workflow framework
langchain>=0.3.13          # LLM orchestration
langchain-core>=0.3.26     # Core LangChain functionality
langchain-openai>=0.2.11   # Azure OpenAI integration

mcp==1.2.0                 # Model Context Protocol client

openai>=1.57.0             # OpenAI Python SDK

python-dotenv>=1.0.1       # Load .env files
pydantic>=2.10.0           # Data validation
pydantic-settings>=2.6.0   # Settings management

httpx>=0.28.0              # HTTP client
aiofiles>=24.1.0           # Async file operations
```

---

## How It Works - Complete Flow

### 1. **Initialization** (main.py)
```python
analyzer = GitHubAnalyzer()
# Loads .env → gets owner, repo, tokens
# Initializes Azure OpenAI client
```

### 2. **MCP Connection** (tools/github_mcp.py)
```python
async with GitHubMCPTools(github_token) as github_tools:
    # Spawns: npx @modelcontextprotocol/server-github
    # Establishes stdio communication
    # Ready to call GitHub MCP tools
```

### 3. **LangGraph Workflow** (main.py)
```
START → explore_repo → analyze_issues → combine → END
         ↓                ↓                ↓
    Repo Agent      Issues Agent     Merge Results
```

### 4. **Repository Exploration** (agents/repository_explorer.py)
```
1. Fetch README.md
2. List src/ directory → find 20 directories
3. Search for .csproj files → find 21 projects
4. LLM identifies services from structure
5. For each service:
   - Fetch {service}.csproj
   - Fetch Program.cs (if executable)
   - LLM extracts: name, description, tech, dependencies
6. LLM analyzes architecture:
   - Service connections (A→B via REST/gRPC)
   - Common patterns (shared technologies)
   - Tech stack overview
```

### 5. **Issues Analysis** (agents/issues_analyzer.py)
```
1. Fetch open issues (50)
2. Fetch closed issues (30)
3. Fetch pull requests (30)
4. LLM categorizes: bugs, features, enhancements, docs
5. Extract metadata: code owners, contributors, affected services
6. Identify patterns: common bugs, feature requests, pain points
```

### 6. **Combine & Save** (main.py)
```python
final_output = {
    "analysis_metadata": {
        "analyzed_at": timestamp,
        "repository": {owner, name},
        "analyzer_version": "1.0.0"
    },
    "repository": {
        "overview": "...",
        "services": [20 services],
        "connections": [33 connections],
        "patterns": {...},
        "tech_stack": [...]
    },
    "issues": {
        "categorized_issues": {...},
        "metadata": {...},
        "patterns": {...}
    }
}

# Save to: output/dotnet_eShop_20251127_033553.json
```

---

## Key Design Principles

### 1. **Generic & Reusable**
- No hardcoded repository names or service lists
- Everything driven by .env configuration
- LLM dynamically discovers structure

### 2. **GitHub MCP Only**
- All data via MCP tools (no direct REST API)
- Efficient: only fetches what's needed
- Respects rate limits automatically

### 3. **Agent Architecture**
- LangGraph orchestrates workflow
- Each agent has single responsibility
- State flows between agents
- Async execution for performance

### 4. **Intelligent Error Handling**
- Silent 404s for expected missing files
- Only fetches Program.cs for executable projects
- Fallback logic when LLM fails

### 5. **LLM-Powered Analysis**
- Uses Azure OpenAI to understand code structure
- Extracts semantic meaning, not just syntax
- Identifies patterns humans would recognize

---

## Output JSON Structure

```json
{
  "analysis_metadata": {
    "analyzed_at": "ISO timestamp",
    "repository": {"owner": "...", "name": "..."},
    "analyzer_version": "1.0.0"
  },
  "repository": {
    "overview": "High-level description",
    "services": [
      {
        "name": "Catalog.API",
        "description": "Manages product catalog...",
        "technologies": [".NET 10", "PostgreSQL", "gRPC"],
        "dependencies": ["Basket.API", "Redis"],
        "type": "api",
        "port": 5101
      }
    ],
    "connections": [
      {"from": "WebApp", "to": "Catalog.API", "method": "REST"}
    ],
    "patterns": {
      "shared_technologies": ["ASP.NET Core", "Redis"],
      "communication_styles": ["REST", "gRPC", "Events"],
      "architecture_pattern": "microservices"
    },
    "tech_stack": [".NET 10", "PostgreSQL", "RabbitMQ"]
  },
  "issues": {
    "summary": {
      "total_open_issues": 50,
      "total_closed_issues": 30,
      "total_prs": 20
    },
    "categorized_issues": {
      "bugs": [{number, title, priority}],
      "features": [{number, title, status}]
    },
    "metadata": {
      "code_owners": ["maintainer1", "maintainer2"],
      "active_contributors": ["dev1", "dev2"],
      "affected_services": ["ServiceA", "ServiceB"]
    },
    "patterns": {
      "common_bug_areas": ["Authentication", "Database"],
      "frequent_feature_requests": ["API v2", "Mobile app"]
    }
  }
}
```

---

## Usage Examples

### Analyze dotnet/eShop
```bash
# .env
GITHUB_REPO_OWNER=dotnet
GITHUB_REPO_NAME=eShop

# Run
python main.py

# Output: output/dotnet_eShop_20251127_033553.json
# Result: 20 services, 33 connections, 30 PRs
```

### Analyze microsoft/semantic-kernel
```bash
# .env
GITHUB_REPO_OWNER=microsoft
GITHUB_REPO_NAME=semantic-kernel

# Run
python main.py

# Output: output/microsoft_semantic-kernel_timestamp.json
```

### Analyze any public repository
```bash
# .env
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo

# Works with any public GitHub repository!
```

---

## Performance Characteristics

- **Execution Time**: ~30-60 seconds for typical repository
- **MCP Calls**: ~20-50 depending on services count
- **LLM Calls**: ~25-30 (service analysis + architecture + issues)
- **Token Usage**: ~10,000-15,000 tokens per analysis
- **Rate Limits**: With GitHub token - 5000 req/hr

---

## Error Handling & Edge Cases

1. **Missing files**: Silently handled with `silent=True`
2. **Non-executable services**: Skips Program.cs fetch
3. **No src/ directory**: Falls back to root directory
4. **LLM parsing errors**: Fallback to label-based categorization
5. **Network errors**: Caught and logged, returns None
6. **Invalid JSON**: Try-catch with sensible defaults

---

This architecture ensures the analyzer works reliably with any GitHub repository while being cost-effective and maintainable.
