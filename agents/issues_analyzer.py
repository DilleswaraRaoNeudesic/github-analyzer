"""
Issues Analyzer Agent
Extracts and analyzes GitHub issues, PRs, and metadata using GitHub MCP
"""
import json
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI


class IssuesAnalyzerAgent:
    """Agent to analyze GitHub issues and pull requests"""
    
    def __init__(self, llm: AzureChatOpenAI, github_tools):
        self.llm = llm
        self.github = github_tools
        self.owner = None
        self.repo = None
    
    def set_repository(self, owner: str, repo: str):
        """Set target repository"""
        self.owner = owner
        self.repo = repo
    
    async def analyze(self) -> Dict[str, Any]:
        """
        Analyze repository issues and pull requests
        Returns structured metadata about issues, features, bugs, etc.
        """
        print(f"\n🐛 Analyzing Issues: {self.owner}/{self.repo}")
        print("=" * 60)
        
        # Step 1: Get open issues
        print("\n📋 Step 1: Fetching open issues...")
        open_issues = await self.github.list_issues(
            self.owner, self.repo, state="open", per_page=100
        )
        open_issues_data = self._parse_issues(open_issues) if open_issues else []
        print(f"  ✅ Found {len(open_issues_data)} open issues")
        
        # Step 2: Get closed issues (recent)
        print("\n📋 Step 2: Fetching closed issues...")
        closed_issues = await self.github.list_issues(
            self.owner, self.repo, state="closed", per_page=50
        )
        closed_issues_data = self._parse_issues(closed_issues) if closed_issues else []
        print(f"  ✅ Found {len(closed_issues_data)} closed issues")
        
        # Step 2.5: Get ALL issues for better analysis
        print("\n📋 Step 2.5: Fetching all issues (open + closed)...")
        all_issues = await self.github.list_issues(
            self.owner, self.repo, state="all", per_page=100
        )
        all_issues_data = self._parse_issues(all_issues) if all_issues else []
        print(f"  ✅ Found {len(all_issues_data)} total issues")
        
        # Step 3: Get pull requests
        print("\n🔀 Step 3: Fetching pull requests...")
        prs = await self.github.list_pull_requests(
            self.owner, self.repo, state="open", per_page=30
        )
        prs_data = self._parse_prs(prs) if prs else []
        print(f"  ✅ Found {len(prs_data)} open PRs")
        
        # Step 4: Extract rich metadata directly
        print("\n📊 Step 4: Extracting issue metadata...")
        metadata = self._extract_direct_metadata(all_issues_data, prs_data)
        
        # Step 5: Calculate statistics
        print("\n📈 Step 5: Calculating statistics...")
        statistics = self._calculate_statistics(all_issues_data, prs_data)
        
        # Step 6: Extract insights from data
        print("\n🔍 Step 6: Analyzing insights...")
        insights = self._extract_insights(all_issues_data, prs_data, metadata)
        
        result = {
            "summary": {
                "total_issues": len(all_issues_data),
                "total_open_issues": len(open_issues_data),
                "total_closed_issues": len(closed_issues_data),
                "total_prs": len(prs_data),
                "open_prs": len([pr for pr in prs_data if pr.get("state") == "open"]),
                "merged_prs": len([pr for pr in prs_data if pr.get("merged_at")])
            },
            "metadata": metadata,
            "statistics": statistics,
            "insights": insights,
            "recent_issues": all_issues_data[:15] if all_issues_data else [],
            "recent_prs": prs_data[:15] if prs_data else []
        }
        
        print("\n✅ Issues analysis complete!")
        print(f"   Total Issues: {len(all_issues_data)}")
        print(f"   Open Issues: {len(open_issues_data)}")
        print(f"   Closed Issues: {len(closed_issues_data)}")
        print(f"   Pull Requests: {len(prs_data)}")
        
        return result
    
    def _parse_issues(self, content: str) -> List[Dict[str, Any]]:
        """Parse issues from GitHub API response"""
        try:
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return [
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "state": issue.get("state"),
                        "labels": [label.get("name") for label in issue.get("labels", []) if label and label.get("name")],
                        "created_at": issue.get("created_at"),
                        "updated_at": issue.get("updated_at"),
                        "user": issue.get("user", {}).get("login") if issue.get("user") else None,
                        "assignees": [a.get("login") for a in issue.get("assignees", []) if a and a.get("login")],
                        "comments": issue.get("comments", 0),
                        "body": issue.get("body", "")[:500] if issue.get("body") else "",
                        "url": issue.get("html_url"),
                        "milestone": issue.get("milestone", {}).get("title") if issue.get("milestone") else None,
                        "closed_at": issue.get("closed_at")
                    }
                    for issue in data
                    if issue and not issue.get("pull_request")  # Filter out PRs from issues list
                ]
            return []
        except Exception as e:
            print(f"  ⚠️  Error parsing issues: {e}")
            return []
    
    def _parse_prs(self, content: str) -> List[Dict[str, Any]]:
        """Parse pull requests from GitHub API response"""
        try:
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return [
                    {
                        "number": pr.get("number"),
                        "title": pr.get("title"),
                        "state": pr.get("state"),
                        "user": pr.get("user", {}).get("login") if pr.get("user") else None,
                        "created_at": pr.get("created_at"),
                        "updated_at": pr.get("updated_at"),
                        "merged_at": pr.get("merged_at"),
                        "closed_at": pr.get("closed_at"),
                        "labels": [label.get("name") for label in pr.get("labels", []) if label and label.get("name")],
                        "draft": pr.get("draft", False),
                        "url": pr.get("html_url"),
                        "body": pr.get("body", "")[:500] if pr.get("body") else "",
                        "assignees": [a.get("login") for a in pr.get("assignees", []) if a and a.get("login")],
                        "requested_reviewers": [r.get("login") for r in pr.get("requested_reviewers", []) if r and r.get("login")],
                        "head": pr.get("head", {}).get("ref") if pr.get("head") else None,
                        "base": pr.get("base", {}).get("ref") if pr.get("base") else None
                    }
                    for pr in data
                    if pr
                ]
            return []
        except Exception as e:
            print(f"  ⚠️  Error parsing PRs: {e}")
            return []
    
    async def _categorize_issues(
        self, 
        open_issues: List[Dict], 
        closed_issues: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """Categorize issues into bugs, features, enhancements, etc."""
        
        all_issues = open_issues + closed_issues[:20]  # Limit for LLM context
        
        prompt = f"""Categorize these GitHub issues into: bugs, features, enhancements, documentation, questions, other.

Issues:
{json.dumps(all_issues, indent=2)[:4000]}

Return JSON:
{{
  "bugs": [{{"number": 123, "title": "...", "priority": "high|medium|low"}}],
  "features": [{{"number": 124, "title": "...", "status": "proposed|in-progress"}}],
  "enhancements": [{{"number": 125, "title": "..."}}],
  "documentation": [{{"number": 126, "title": "..."}}],
  "questions": [{{"number": 127, "title": "..."}}],
  "other": [{{"number": 128, "title": "..."}}]
}}
"""
        
        response = await self.llm.ainvoke([
            SystemMessage(content="You are an issue triage expert. Return only valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        try:
            return json.loads(response.content.strip().replace("```json", "").replace("```", ""))
        except:
            # Fallback: use labels
            return self._categorize_by_labels(all_issues)
    
    def _categorize_by_labels(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """Fallback categorization using labels"""
        categories = {
            "bugs": [],
            "features": [],
            "enhancements": [],
            "documentation": [],
            "questions": [],
            "other": []
        }
        
        for issue in issues:
            labels = [l.lower() for l in issue.get("labels", [])]
            if any(l in labels for l in ["bug", "defect", "error"]):
                categories["bugs"].append(issue)
            elif any(l in labels for l in ["feature", "enhancement"]):
                categories["features"].append(issue)
            elif "documentation" in labels or "docs" in labels:
                categories["documentation"].append(issue)
            elif "question" in labels:
                categories["questions"].append(issue)
            else:
                categories["other"].append(issue)
        
        return categories
    
    async def _extract_metadata(
        self,
        all_issues: List[Dict],
        prs: List[Dict]
    ) -> Dict[str, Any]:
        """Extract metadata: code owners, tech stack, affected services"""
        
        # Get label distribution
        label_counts = {}
        for issue in all_issues:
            for label in issue.get("labels", []):
                label_counts[label] = label_counts.get(label, 0) + 1
        
        # Get top contributors
        contributors = {}
        for issue in all_issues:
            user = issue.get("user")
            if user:
                contributors[user] = contributors.get(user, 0) + 1
        for pr in prs:
            user = pr.get("user")
            if user:
                contributors[user] = contributors.get(user, 0) + 1
        
        top_contributors = sorted(contributors.items(), key=lambda x: x[1], reverse=True)[:15]
        
        prompt = f"""Extract metadata from these issues and PRs:

Issues (sample):
{json.dumps(all_issues[:20], indent=2)}

Pull Requests (sample):
{json.dumps(prs[:15], indent=2)}

Label Distribution:
{json.dumps(label_counts, indent=2)}

Top Contributors:
{json.dumps(dict(top_contributors), indent=2)}

Extract and return JSON:
{{
  "code_owners": ["username1", "username2"],
  "active_contributors": ["user1", "user2", "user3"],
  "affected_services": ["Service1", "Service2"],
  "common_technologies": ["tech1", "tech2"],
  "issue_labels": {{"label1": count, "label2": count}},
  "common_issue_themes": ["theme1", "theme2"]
}}
"""
        
        response = await self.llm.ainvoke([
            SystemMessage(content="You are a metadata extraction expert. Return only valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        try:
            return json.loads(response.content.strip().replace("```json", "").replace("```", ""))
        except:
            return {
                "code_owners": list(set([i.get("user") for i in all_issues if i.get("user")][:10])),
                "active_contributors": [user for user, _ in top_contributors],
                "affected_services": [],
                "common_technologies": [],
                "issue_labels": label_counts,
                "common_issue_themes": []
            }
    
    def _extract_direct_metadata(
        self,
        all_issues: List[Dict],
        prs: List[Dict]
    ) -> Dict[str, Any]:
        """Extract metadata directly from issues without LLM"""
        
        # Label distribution
        label_counts = {}
        for issue in all_issues:
            for label in issue.get("labels", []):
                label_counts[label] = label_counts.get(label, 0) + 1
        
        # User activity
        issue_authors = {}
        pr_authors = {}
        assignees_list = []
        
        for issue in all_issues:
            user = issue.get("user")
            if user:
                issue_authors[user] = issue_authors.get(user, 0) + 1
            assignees_list.extend(issue.get("assignees", []))
        
        for pr in prs:
            user = pr.get("user")
            if user:
                pr_authors[user] = pr_authors.get(user, 0) + 1
            assignees_list.extend(pr.get("assignees", []))
        
        # Milestone tracking
        milestones = {}
        for issue in all_issues:
            milestone = issue.get("milestone")
            if milestone:
                milestones[milestone] = milestones.get(milestone, 0) + 1
        
        # Issue types by label
        bugs = [i for i in all_issues if any('bug' in l.lower() for l in i.get("labels", []))]
        features = [i for i in all_issues if any('feature' in l.lower() or 'enhancement' in l.lower() for l in i.get("labels", []))]
        docs = [i for i in all_issues if any('doc' in l.lower() for l in i.get("labels", []))]
        
        return {
            "labels": dict(sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
            "top_issue_creators": dict(sorted(issue_authors.items(), key=lambda x: x[1], reverse=True)[:10]),
            "top_pr_creators": dict(sorted(pr_authors.items(), key=lambda x: x[1], reverse=True)[:10]),
            "top_assignees": dict(sorted(
                {a: assignees_list.count(a) for a in set(assignees_list)}.items(),
                key=lambda x: x[1], reverse=True
            )[:10]),
            "milestones": milestones,
            "issue_counts_by_type": {
                "bugs": len(bugs),
                "features": len(features),
                "documentation": len(docs)
            }
        }
    
    def _extract_insights(
        self,
        all_issues: List[Dict],
        prs: List[Dict],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract insights from the data"""
        
        # Get issues with most comments
        highly_discussed = sorted(
            [i for i in all_issues if i.get("comments", 0) > 5],
            key=lambda x: x.get("comments", 0),
            reverse=True
        )[:10]
        
        # Recently updated issues
        recently_active = sorted(
            all_issues,
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )[:10]
        
        # Open issues without assignees
        unassigned_open = [
            i for i in all_issues 
            if i.get("state") == "open" and not i.get("assignees")
        ]
        
        # Draft PRs
        draft_prs = [pr for pr in prs if pr.get("draft")]
        
        # PRs awaiting review
        awaiting_review = [
            pr for pr in prs 
            if pr.get("state") == "open" and not pr.get("requested_reviewers")
        ]
        
        return {
            "highly_discussed_issues": [
                {"number": i.get("number"), "title": i.get("title"), "comments": i.get("comments")}
                for i in highly_discussed
            ],
            "recently_active_issues": [
                {"number": i.get("number"), "title": i.get("title"), "updated_at": i.get("updated_at")}
                for i in recently_active
            ],
            "unassigned_open_issues_count": len(unassigned_open),
            "draft_prs_count": len(draft_prs),
            "prs_awaiting_review_count": len(awaiting_review),
            "most_used_labels": list(metadata.get("labels", {}).keys())[:10]
        }
    
    def _calculate_statistics(
        self,
        all_issues: List[Dict],
        prs: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate statistics from issues and PRs"""
        
        # Issues with most comments
        top_discussed = sorted(
            [i for i in all_issues if i.get("comments", 0) > 0],
            key=lambda x: x.get("comments", 0),
            reverse=True
        )[:10]
        
        # Label distribution
        label_counts = {}
        for issue in all_issues:
            for label in issue.get("labels", []):
                label_counts[label] = label_counts.get(label, 0) + 1
        
        # Milestone tracking
        milestone_counts = {}
        for issue in all_issues:
            milestone = issue.get("milestone")
            if milestone:
                milestone_counts[milestone] = milestone_counts.get(milestone, 0) + 1
        
        # PR statistics
        pr_stats = {
            "total": len(prs),
            "open": len([pr for pr in prs if pr.get("state") == "open"]),
            "merged": len([pr for pr in prs if pr.get("merged_at")]),
            "draft": len([pr for pr in prs if pr.get("draft")]),
            "with_assignees": len([pr for pr in prs if pr.get("assignees")])
        }
        
        return {
            "most_discussed_issues": [
                {"number": i.get("number"), "title": i.get("title"), "comments": i.get("comments")}
                for i in top_discussed
            ],
            "label_distribution": dict(sorted(label_counts.items(), key=lambda x: x[1], reverse=True)),
            "milestone_distribution": milestone_counts,
            "pr_statistics": pr_stats
        }
    
    async def _identify_patterns(
        self,
        categorized: Dict[str, List],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify patterns in issues"""
        
        prompt = f"""Analyze these categorized issues to identify patterns:

Categorized Issues:
{json.dumps(categorized, indent=2)[:3000]}

Metadata:
{json.dumps(metadata, indent=2)}

Identify patterns and return JSON:
{{
  "common_bug_areas": ["area1", "area2"],
  "frequent_feature_requests": ["feature type 1", "feature type 2"],
  "pain_points": ["pain point 1", "pain point 2"],
  "improvement_opportunities": ["opportunity 1", "opportunity 2"]
}}
"""
        
        response = await self.llm.ainvoke([
            SystemMessage(content="You are a pattern analysis expert. Return only valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        try:
            return json.loads(response.content.strip().replace("```json", "").replace("```", ""))
        except:
            return {
                "common_bug_areas": [],
                "frequent_feature_requests": [],
                "pain_points": [],
                "improvement_opportunities": []
            }
    
    def _get_recent_activity(
        self,
        recent_issues: List[Dict],
        recent_prs: List[Dict]
    ) -> Dict[str, List]:
        """Get recent activity summary"""
        return {
            "recent_issues": [
                {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "created_at": issue.get("created_at")
                }
                for issue in recent_issues
            ],
            "recent_prs": [
                {
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "created_at": pr.get("created_at")
                }
                for pr in recent_prs
            ]
        }
