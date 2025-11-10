"""
This file contains the concrete implementations of the abstract 'Step' class.

Each class here represents a "real" action that pypipe can run
or transpile, like executing a shell command or checking out code.
"""

import shlex
import subprocess # nosec B404: subprocess is used with argv-only
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# Import the abstract base class from our models
from .models import Step


@dataclass
class RunShellStep(Step):
    """A step that executes a shell command."""
    
    command: str = field(default="")
    name: str = field(default="")
    """The shell command to execute (e.g., "pytest")."""

    def execute(self, context: Any) -> None:
        """
        Executes the shell command using subprocess.
        The 'context' can be used
        to pass environment variables or secrets.
        """
        print(f"--- Running Step: {self.name}")
        try:
            argv = shlex.split(self.command)

            subprocess.run(
                argv, 
                shell=False, 
                check=True,
                text=True, 
                encoding='utf-8'
            ) # nosec B603
            
        except subprocess.CalledProcessError as e:
            print(f"Step '{self.name}' failed with exit code {e.returncode}")
            raise e # Re-raise to stop the pipeline
        except Exception as e:
            print(f"Step '{self.name}' failed with an unexpected error: {e}")
            raise e

    def to_github_dict(self) -> Dict[str, Any]:
        """Transpiles to the GitHub Actions YAML format."""
        return {
            "run": self.command
        }
        
@dataclass
class CheckoutStep(Step):
    """
    A step that checks out source code.
    
    This is a common "special" step in most CI systems.
    """
    
    repository: Optional[str] = None
    """(Optional) The repo to checkout (e.g., "user/repo")."""
    
    ref: Optional[str] = None
    """(Optional) The branch, tag, or SHA to checkout."""

    def execute(self, context: Any) -> None:
        """Runs 'git clone' locally."""
        print("--- Running step:")
        
        # This is a simplified implementation.
        # A real one would handle auth, refs, etc.
        cmd = "git clone"
        if self.repository:
            # This is a placeholder; a real implementation
            # would need to construct a full URL.
            cmd += f" https://github.com/{self.repository}.git"
        

        print(f"[Simulating] {cmd}")


    def to_github_dict(self) -> Dict[str, Any]:
        """Translates to the 'actions/checkout' reusable action."""
        # This step is special in GitHub, it uses 'uses'
        github_dict: Dict[str, Any] = {
            "uses": "actions/checkout@v4"
        }

        # Add 'with' block if we have details
        with_details = {}
        if self.repository:
            with_details["repository"] = self.repository
        if self.ref:
            with_details["ref"] = self.ref
        
        if with_details:
            github_dict["with"] = with_details
            
        return github_dict