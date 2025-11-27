"""
GitHub MCP Tools Wrapper
Provides clean interface to GitHub MCP server tools
"""
import os
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GitHubMCPTools:
    """Wrapper for GitHub MCP server tools"""
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Context manager entry - connect to MCP server"""
        # Use full path to npx on Windows
        import shutil
        npx_cmd = shutil.which("npx") or "npx.cmd"
        
        server_params = StdioServerParameters(
            command=npx_cmd,
            args=["-y", "@modelcontextprotocol/server-github"],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token,
                **os.environ
            }
        )
        
        self.stdio_context = stdio_client(server_params)
        self.read, self.write = await self.stdio_context.__aenter__()
        
        self.session_context = ClientSession(self.read, self.write)
        self.session = await self.session_context.__aenter__()
        await self.session.initialize()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        if self.session:
            await self.session_context.__aexit__(exc_type, exc_val, exc_tb)
        if hasattr(self, 'stdio_context'):
            await self.stdio_context.__aexit__(exc_type, exc_val, exc_tb)
    
    async def get_file_contents(
        self, 
        owner: str, 
        repo: str, 
        path: str,
        branch: Optional[str] = None,
        silent: bool = False
    ) -> Optional[str]:
        """Get contents of a file or directory"""
        try:
            args = {"owner": owner, "repo": repo, "path": path}
            if branch:
                args["branch"] = branch
                
            result = await self.session.call_tool("get_file_contents", arguments=args)
            
            if result and hasattr(result, 'content'):
                for item in result.content:
                    if hasattr(item, 'text'):
                        return item.text
            return None
        except Exception as e:
            if not silent:
                # Only print errors for unexpected issues, not 404s
                if "Not Found" not in str(e):
                    print(f"Error getting {path}: {e}")
            return None
    
    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
        page: int = 1
    ) -> Optional[str]:
        """List issues in repository"""
        try:
            result = await self.session.call_tool(
                "list_issues",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "state": state,
                    "per_page": per_page,
                    "page": page
                }
            )
            
            if result and hasattr(result, 'content'):
                for item in result.content:
                    if hasattr(item, 'text'):
                        return item.text
            return None
        except Exception as e:
            print(f"Error listing issues: {e}")
            return None
    
    async def get_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int
    ) -> Optional[str]:
        """Get details of specific issue"""
        try:
            result = await self.session.call_tool(
                "get_issue",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "issue_number": issue_number
                }
            )
            
            if result and hasattr(result, 'content'):
                for item in result.content:
                    if hasattr(item, 'text'):
                        return item.text
            return None
        except Exception as e:
            print(f"Error getting issue #{issue_number}: {e}")
            return None
    
    async def search_code(
        self,
        owner: str,
        repo: str,
        query: str,
        per_page: int = 10
    ) -> Optional[str]:
        """Search code in repository"""
        try:
            search_query = f"{query} repo:{owner}/{repo}"
            result = await self.session.call_tool(
                "search_code",
                arguments={
                    "q": search_query,
                    "per_page": per_page
                }
            )
            
            if result and hasattr(result, 'content'):
                for item in result.content:
                    if hasattr(item, 'text'):
                        return item.text
            return None
        except Exception as e:
            print(f"Error searching code: {e}")
            return None
    
    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30
    ) -> Optional[str]:
        """List pull requests"""
        try:
            result = await self.session.call_tool(
                "list_pull_requests",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "state": state,
                    "per_page": per_page
                }
            )
            
            if result and hasattr(result, 'content'):
                for item in result.content:
                    if hasattr(item, 'text'):
                        return item.text
            return None
        except Exception as e:
            print(f"Error listing PRs: {e}")
            return None
