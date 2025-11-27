"""
GitHub Repository Analyzer - Main Application
Uses LangGraph agents to analyze any GitHub repository
"""
import os
import json
import asyncio
from datetime import datetime
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END

from tools.github_mcp import GitHubMCPTools
from agents.repository_explorer import RepositoryExplorerAgent
from agents.issues_analyzer import IssuesAnalyzerAgent


# Define the state of our workflow
class AnalysisState(TypedDict):
    """State passed between agents in the workflow"""
    repository: dict  # owner, name
    repository_analysis: dict  # from RepositoryExplorerAgent
    issues_analysis: dict  # from IssuesAnalyzerAgent
    final_output: dict  # combined results
    status: str  # workflow status


class GitHubAnalyzer:
    """Main analyzer coordinating agents with LangGraph"""
    
    def __init__(self):
        load_dotenv()
        
        # Configuration
        self.owner = os.getenv("GITHUB_REPO_OWNER")
        self.repo = os.getenv("GITHUB_REPO_NAME")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.output_dir = os.getenv("OUTPUT_DIR", "output")
        
        # Initialize LLM
        self.llm = AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            temperature=0.1
        )
        
        print(f"\n🚀 GitHub Repository Analyzer")
        print(f"=" * 60)
        print(f"Target: {self.owner}/{self.repo}")
        print(f"=" * 60)
    
    async def analyze(self):
        """Run the analysis workflow"""
        
        # Initialize GitHub MCP tools
        async with GitHubMCPTools(self.github_token) as github_tools:
            # Initialize agents
            repo_explorer = RepositoryExplorerAgent(self.llm, github_tools)
            repo_explorer.set_repository(self.owner, self.repo)
            
            issues_analyzer = IssuesAnalyzerAgent(self.llm, github_tools)
            issues_analyzer.set_repository(self.owner, self.repo)
            
            # Create LangGraph workflow
            workflow = StateGraph(AnalysisState)
            
            # Define nodes
            async def explore_repository(state: AnalysisState) -> AnalysisState:
                """Node: Explore repository structure and services"""
                print("\n" + "=" * 60)
                print("NODE: Repository Explorer")
                print("=" * 60)
                
                result = await repo_explorer.explore()
                state["repository_analysis"] = result
                state["status"] = "repository_explored"
                return state
            
            async def analyze_issues(state: AnalysisState) -> AnalysisState:
                """Node: Analyze issues and PRs"""
                print("\n" + "=" * 60)
                print("NODE: Issues Analyzer")
                print("=" * 60)
                
                result = await issues_analyzer.analyze()
                state["issues_analysis"] = result
                state["status"] = "issues_analyzed"
                return state
            
            async def combine_results(state: AnalysisState) -> AnalysisState:
                """Node: Combine all analysis results"""
                print("\n" + "=" * 60)
                print("NODE: Combining Results")
                print("=" * 60)
                
                final_output = {
                    "analysis_metadata": {
                        "analyzed_at": datetime.now().isoformat(),
                        "repository": state["repository"],
                        "analyzer_version": "1.0.0"
                    },
                    "repository": state["repository_analysis"],
                    "issues": state["issues_analysis"]
                }
                
                state["final_output"] = final_output
                state["status"] = "completed"
                
                print("✅ Results combined successfully")
                return state
            
            # Add nodes to graph
            workflow.add_node("explore_repo", explore_repository)
            workflow.add_node("analyze_issues", analyze_issues)
            workflow.add_node("combine", combine_results)
            
            # Define edges (workflow flow)
            workflow.set_entry_point("explore_repo")
            workflow.add_edge("explore_repo", "analyze_issues")
            workflow.add_edge("analyze_issues", "combine")
            workflow.add_edge("combine", END)
            
            # Compile the graph
            app = workflow.compile()
            
            # Initialize state
            initial_state: AnalysisState = {
                "repository": {
                    "owner": self.owner,
                    "name": self.repo
                },
                "repository_analysis": {},
                "issues_analysis": {},
                "final_output": {},
                "status": "initialized"
            }
            
            # Run the workflow
            print("\n" + "=" * 60)
            print("STARTING LANGGRAPH WORKFLOW")
            print("=" * 60)
            
            final_state = await app.ainvoke(initial_state)
            
            # Save output
            self._save_output(final_state["final_output"])
            
            return final_state["final_output"]
    
    def _save_output(self, output: dict):
        """Save analysis output to file"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.owner}_{self.repo}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n" + "=" * 60)
        print(f"✅ ANALYSIS COMPLETE")
        print(f"=" * 60)
        print(f"📁 Output saved to: {filepath}")
        print(f"📊 Services found: {len(output.get('repository', {}).get('services', []))}")
        print(f"🐛 Open issues: {output.get('issues', {}).get('summary', {}).get('total_open_issues', 0)}")
        print(f"🔗 Connections: {len(output.get('repository', {}).get('connections', []))}")
        print("=" * 60)


async def main():
    """Main entry point"""
    analyzer = GitHubAnalyzer()
    await analyzer.analyze()


if __name__ == "__main__":
    asyncio.run(main())
