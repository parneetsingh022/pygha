"""
Core data models for pypipe.

These classes define the "blueprint" of a pipeline.
They are "dumb" data containers. The logic that runs or
transpiles them lives in other modules (like runner.py).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from collections import deque

# --- Step Base Class ---
# We define a simple base class for Step so that the
# Job class can have a type-hinted list of steps.
@dataclass
class Step:
    """Abstract base class for all pipeline steps."""
    name: str = ""

    def execute(self, context: Any) -> None:
        """The method the LocalRunner will call."""
        raise NotImplementedError

    def to_github_dict(self) -> Dict[str, Any]:
        """The method the GitHub Transpiler will call."""
        raise NotImplementedError
    
    def to_gitlab_dict(self) -> Dict[str, Any]:
        """The method the GitLab Transpiler will call."""
        raise NotImplementedError
    

# --- Job Object ---

@dataclass
class Job:
    """
    Represents a single unit of work in the pipeline, like "build" or "test".
    It holds a list of steps to run and a set of dependencies.
    """
    name: str
    """The unique name of the job (e.g., "build")."""

    steps: List[Step] = field(default_factory=list)
    """The list of Step objects to be executed in order."""

    depends_on: Set[str] = field(default_factory=set)
    """A set of job names that this job depends on (e.g., {"build"})."""
    
    runner_image: Optional[str] = None
    """(Optional) The container image to run this job in (e.g., "ubuntu-latest")."""

    def add_step(self, step: Step) -> None:
        """A simple helper to add a step to this job."""
        self.steps.append(step)


# --- Pipeline Object ---

@dataclass
class Pipeline:
    """
    The main container for the entire CI/CD workflow.
    
    This object holds all the Job objects and contains the logic
    to resolve their execution order.
    """
    
    jobs: Dict[str, Job] = field(default_factory=dict)
    """A dictionary mapping job names to the Job objects."""

    def add_job(self, job: Job) -> None:
        """Registers a new job with the pipeline."""
        if job.name in self.jobs:
            raise ValueError(f"A job with the name '{job.name}' already exists.")
        self.jobs[job.name] = job

    def get_job_order(self) -> List[Job]:
        """
        Calculates the correct execution order for all jobs.
        
        This is the "brain" of pypipe. It performs a topological sort
        on the job graph and detects circular dependencies.

        Returns:
            A list of Job objects in the correct order of execution.
        """
        
        # 1. Build the graph representations
        #    - adj: Adjacency list (job -> list of jobs that depend on it)
        #    - in_degree: Count of dependencies for each job
        
        adj: Dict[str, List[str]] = {name: [] for name in self.jobs}
        in_degree: Dict[str, int] = {name: 0 for name in self.jobs}
        
        for name, job in self.jobs.items():
            for dep_name in job.depends_on:
                # Check for invalid dependencies
                if dep_name not in self.jobs:
                    raise ValueError(
                        f"Job '{name}' has an invalid dependency: '{dep_name}'"
                    )
                
                # A depends on B means an edge from B -> A
                adj[dep_name].append(name)
                in_degree[name] += 1
        
        # 2. Initialize the queue with all "source" jobs (no dependencies)
        queue = deque([name for name in self.jobs if in_degree[name] == 0])
        sorted_names = []
        
        # 3. Process the queue (Kahn's algorithm for topological sort)
        while queue:
            job_name = queue.popleft()
            sorted_names.append(job_name)
            
            # For each job that depended on the one we just finished...
            for next_job_name in adj[job_name]:
                # ...decrement its dependency count
                in_degree[next_job_name] -= 1
                # If it now has no more dependencies, add it to the queue
                if in_degree[next_job_name] == 0:
                    queue.append(next_job_name)
                    
        # 4. Check for cycles
        if len(sorted_names) != len(self.jobs):
            # A cycle was detected!
            cycle_jobs = {
                name for name in self.jobs if in_degree[name] > 0
            }
            raise ValueError(
                f"Circular dependency detected! Jobs in cycle: {cycle_jobs}"
            )
            
        # 5. Return the full Job objects in the correct order
        return [self.jobs[name] for name in sorted_names]