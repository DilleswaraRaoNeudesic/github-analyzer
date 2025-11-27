"""
Repository Explorer Agent
Dynamically discovers repository structure and services using GitHub MCP
"""
import json
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI


class RepositoryExplorerAgent:
    """Agent to explore repository and discover services/structure"""
    
    def __init__(self, llm: AzureChatOpenAI, github_tools):
        self.llm = llm
        self.github = github_tools
        self.owner = None
        self.repo = None
    
    def set_repository(self, owner: str, repo: str):
        """Set target repository"""
        self.owner = owner
        self.repo = repo
    
    async def explore(self) -> Dict[str, Any]:
        """
        Explore repository structure dynamically
        Returns structured information about the repository
        """
        print(f"\n🔍 Exploring Repository: {self.owner}/{self.repo}")
        print("=" * 60)
        
        # Step 1: Get main README
        print("\n📖 Step 1: Fetching README...")
        readme = await self.github.get_file_contents(self.owner, self.repo, "README.md")
        
        if not readme:
            print("  ⚠️  No README found")
            readme = "No README available"
        else:
            print(f"  ✅ README fetched ({len(readme)} chars)")
        
        # Step 2: Explore src directory
        print("\n📁 Step 2: Exploring src/ directory...")
        src_structure = await self.github.get_file_contents(self.owner, self.repo, "src")
        
        if not src_structure:
            print("  ⚠️  No src/ directory, trying root...")
            src_structure = await self.github.get_file_contents(self.owner, self.repo, "")
        
        directories = self._parse_directory_structure(src_structure) if src_structure else []
        print(f"  ✅ Found {len(directories)} directories")
        
        # Step 3: Search for project files to identify services
        print("\n🔎 Step 3: Searching for project files...")
        csproj_results = await self.github.search_code(
            self.owner, self.repo, "extension:csproj", per_page=30
        )
        
        project_files = self._parse_search_results(csproj_results) if csproj_results else []
        print(f"  ✅ Found {len(project_files)} project files")
        
        # Step 4: Identify services using LLM
        print("\n🤖 Step 4: Analyzing with LLM to identify services...")
        services = await self._identify_services(readme, directories, project_files)
        
        # Step 5: Get detailed info for each service
        print(f"\n📊 Step 5: Fetching details for {len(services)} services...")
        detailed_services = await self._get_service_details(services)
        
        # Step 6: Analyze connections and patterns
        print("\n🔗 Step 6: Analyzing service connections...")
        analysis = await self._analyze_architecture(readme, detailed_services)
        
        # Step 7: Extract additional repository metadata
        print("\n📚 Step 7: Extracting repository metadata...")
        repo_metadata = await self._extract_repository_metadata(self.github)
        
        result = {
            "repository": {
                "owner": self.owner,
                "name": self.repo,
                "url": f"https://github.com/{self.owner}/{self.repo}"
            },
            "overview": analysis.get("overview", ""),
            "metadata": repo_metadata,
            "services": detailed_services,
            "connections": analysis.get("connections", []),
            "patterns": analysis.get("patterns", {}),
            "tech_stack": analysis.get("tech_stack", [])
        }
        
        print("\n✅ Repository exploration complete!")
        print(f"   Services: {len(detailed_services)}")
        print(f"   Connections: {len(result['connections'])}")
        
        return result
    
    def _parse_directory_structure(self, content: str) -> List[Dict[str, str]]:
        """Parse directory listing from GitHub API response"""
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return [
                    {"name": item.get("name"), "path": item.get("path"), "type": item.get("type")}
                    for item in data
                    if item.get("type") == "dir"
                ]
            return []
        except:
            return []
    
    def _parse_search_results(self, content: str) -> List[Dict[str, str]]:
        """Parse search results from GitHub"""
        try:
            data = json.loads(content)
            items = data.get("items", [])
            return [
                {"name": item.get("name"), "path": item.get("path")}
                for item in items
            ]
        except:
            return []
    
    async def _identify_services(
        self, 
        readme: str, 
        directories: List[Dict], 
        project_files: List[Dict]
    ) -> List[str]:
        """Use LLM to identify services from repository structure"""
        
        prompt = f"""You are analyzing a GitHub repository to identify services/applications.

README Content (first 3000 chars):
{readme[:3000]}

Directories found:
{json.dumps(directories[:20], indent=2)}

Project files found:
{json.dumps(project_files[:20], indent=2)}

Based on this information, identify ALL services/applications in this repository.
Look for:
- API services (e.g., Catalog.API, Basket.API)
- Web applications (e.g., WebApp, ClientApp)
- Background services
- Infrastructure/shared libraries (e.g., EventBus, ServiceDefaults)

Return ONLY a JSON array of service names (directory/folder names):
["Service1", "Service2", "Service3"]
"""
        
        response = await self.llm.ainvoke([
            SystemMessage(content="You are a repository analysis expert. Return only valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        try:
            services = json.loads(response.content.strip().replace("```json", "").replace("```", ""))
            return services if isinstance(services, list) else []
        except:
            # Fallback: extract from directories
            return [d["name"] for d in directories if any(
                keyword in d["name"].lower() 
                for keyword in ["api", "service", "app", "web", "client"]
            )]
    
    async def _get_service_details(self, services: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information for each identified service"""
        detailed_services = []
        
        for service in services:
            print(f"   • Analyzing {service}...", end=" ")
            
            # Try to get project file (suppress 404 errors)
            project_file_path = f"src/{service}/{service}.csproj"
            project_content = await self.github.get_file_contents(
                self.owner, self.repo, project_file_path, silent=True
            )
            
            # Try Program.cs only if project file exists or is likely an executable
            program_cs = ""
            if project_content or any(x in service.lower() for x in [".api", "app", "processor", "client", "web"]):
                program_cs_path = f"src/{service}/Program.cs"
                program_cs = await self.github.get_file_contents(
                    self.owner, self.repo, program_cs_path, silent=True
                ) or ""
            
            # Show status
            if project_content or program_cs:
                print("✓")
            else:
                print("⚠ (minimal metadata)")
            
            # Analyze service with LLM
            service_info = await self._analyze_service(
                service, project_content or "", program_cs
            )
            
            detailed_services.append(service_info)
        
        return detailed_services
    
    async def _analyze_service(
        self, 
        service_name: str, 
        project_file: str, 
        program_cs: str
    ) -> Dict[str, Any]:
        """Analyze individual service to extract metadata"""
        
        prompt = f"""Analyze this service and extract information:

Service Name: {service_name}

Project File (.csproj):
{project_file[:2000] if project_file else "Not available"}

Program.cs:
{program_cs[:2000] if program_cs else "Not available"}

Extract and return JSON with:
{{
  "name": "service name",
  "description": "what this service does (concrete, specific)",
  "technologies": ["tech1", "tech2"],
  "dependencies": ["dependency1", "dependency2"],
  "type": "api|webapp|library|service",
  "port": "port number if found or null"
}}
"""
        
        response = await self.llm.ainvoke([
            SystemMessage(content="You are a code analysis expert. Return only valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        try:
            return json.loads(response.content.strip().replace("```json", "").replace("```", ""))
        except:
            return {
                "name": service_name,
                "description": "Service information not available",
                "technologies": [],
                "dependencies": [],
                "type": "unknown",
                "port": None
            }
    
    async def _extract_repository_metadata(self, session) -> Dict[str, Any]:
        """Extract repository metadata files and structure"""
        metadata = {}
        
        # Check for common metadata files
        metadata_files = {
            "license": ["LICENSE", "LICENSE.md", "LICENSE.txt"],
            "contributing": ["CONTRIBUTING.md", "CONTRIBUTING", ".github/CONTRIBUTING.md"],
            "code_of_conduct": ["CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md"],
            "security": ["SECURITY.md", ".github/SECURITY.md"],
            "changelog": ["CHANGELOG.md", "CHANGELOG", "HISTORY.md"]
        }
        
        for key, paths in metadata_files.items():
            for path in paths:
                content = await self.github.get_file_contents(self.owner, self.repo, path, silent=True)
                if content:
                    metadata[key] = {"exists": True, "path": path, "content_preview": content[:200]}
                    break
            if key not in metadata:
                metadata[key] = {"exists": False}
        
        # Check for GitHub Actions workflows
        workflows_dir = await self.github.get_file_contents(self.owner, self.repo, ".github/workflows", silent=True)
        if workflows_dir:
            try:
                workflows_data = json.loads(workflows_dir)
                if isinstance(workflows_data, list):
                    metadata["ci_cd_workflows"] = [
                        {"name": w.get("name"), "path": w.get("path")}
                        for w in workflows_data if w.get("type") == "file"
                    ]
            except:
                metadata["ci_cd_workflows"] = []
        else:
            metadata["ci_cd_workflows"] = []
        
        # Check for Docker support
        dockerfile = await self.github.get_file_contents(self.owner, self.repo, "Dockerfile", silent=True)
        docker_compose = await self.github.get_file_contents(self.owner, self.repo, "docker-compose.yml", silent=True)
        metadata["docker_support"] = {
            "dockerfile": dockerfile is not None,
            "docker_compose": docker_compose is not None
        }
        
        # Check for documentation
        docs_dir = await self.github.get_file_contents(self.owner, self.repo, "docs", silent=True)
        metadata["documentation"] = {"has_docs_folder": docs_dir is not None}
        
        # Check for tests
        test_dirs = ["tests", "test", "Tests", "Test"]
        test_found = False
        for test_dir in test_dirs:
            test_content = await self.github.get_file_contents(self.owner, self.repo, test_dir, silent=True)
            if test_content:
                test_found = True
                break
        metadata["testing"] = {"has_test_directory": test_found}
        
        return metadata
    
    async def _analyze_architecture(
        self, 
        readme: str, 
        services: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze overall architecture, connections, and patterns"""
        
        prompt = f"""Analyze this repository's architecture:

README:
{readme[:4000]}

Services:
{json.dumps(services, indent=2)}

Provide JSON with:
{{
  "overview": "brief description of the repository",
  "connections": [
    {{"from": "ServiceA", "to": "ServiceB", "method": "REST|gRPC|Events"}}
  ],
  "patterns": {{
    "shared_technologies": ["tech1", "tech2"],
    "communication_styles": ["REST", "Events"],
    "architecture_pattern": "microservices|monolith|modular"
  }},
  "tech_stack": ["primary technologies used"]
}}
"""
        
        response = await self.llm.ainvoke([
            SystemMessage(content="You are an architecture analysis expert. Return only valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        try:
            return json.loads(response.content.strip().replace("```json", "").replace("```", ""))
        except:
            return {
                "overview": "Analysis not available",
                "connections": [],
                "patterns": {},
                "tech_stack": []
            }
