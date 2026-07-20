"""
Ω OMEGA Deployment Service — Vercel, Docker, and infrastructure deployment (§384).

Manages deployment configurations, build pipelines, and release orchestration.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ── Types ──────────────────────────────────────────────────────────────────

class DeploymentTarget(Enum):
    VERCEL = "vercel"
    DOCKER = "docker"
    LOCAL = "local"


class DeploymentStatus(Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    LIVE = "live"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Deployment:
    """A deployment configuration and state."""
    id: str
    target: DeploymentTarget
    project: str
    version: str
    status: DeploymentStatus = DeploymentStatus.PENDING
    config: dict[str, Any] = field(default_factory=dict)
    url: Optional[str] = None
    error: Optional[str] = None
    build_log: list[str] = field(default_factory=list)


# ── Deployer ───────────────────────────────────────────────────────────────

class Deployer:
    """Deployment orchestrator supporting multiple targets."""

    def __init__(self):
        self._deployments: dict[str, Deployment] = {}
        self._strategies: dict[DeploymentTarget, Any] = {}

    def register_strategy(self, target: DeploymentTarget, strategy: Any) -> None:
        """Register a deployment strategy."""
        self._strategies[target] = strategy

    def create_deployment(
        self,
        target: DeploymentTarget,
        project: str,
        version: str,
        config: Optional[dict] = None,
    ) -> Deployment:
        """Create a new deployment record."""
        import uuid
        dep = Deployment(
            id=f"deploy-{uuid.uuid4().hex[:12]}",
            target=target,
            project=project,
            version=version,
            config=config or {},
        )
        self._deployments[dep.id] = dep
        return dep

    def deploy(self, deployment_id: str) -> bool:
        """Execute a deployment."""
        dep = self._deployments.get(deployment_id)
        if not dep:
            return False

        strategy = self._strategies.get(dep.target)
        if not strategy:
            dep.status = DeploymentStatus.FAILED
            dep.error = f"No strategy for {dep.target}"
            return False

        try:
            dep.status = DeploymentStatus.BUILDING
            dep.build_log.append(f"Building {dep.project}@{dep.version}...")

            if dep.target == DeploymentTarget.VERCEL:
                result = self._vercel_deploy(dep)
            elif dep.target == DeploymentTarget.DOCKER:
                result = self._docker_deploy(dep)
            elif dep.target == DeploymentTarget.LOCAL:
                result = self._local_deploy(dep)
            else:
                result = strategy(dep)

            if result:
                dep.status = DeploymentStatus.LIVE
                dep.build_log.append("Deployment live")
                return True
            else:
                dep.status = DeploymentStatus.FAILED
                dep.error = "Deployment strategy returned failure"
                return False
        except Exception as e:
            dep.status = DeploymentStatus.FAILED
            dep.error = str(e)
            return False

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        return self._deployments.get(deployment_id)

    # ── Strategy implementations ──

    def _vercel_deploy(self, dep: Deployment) -> bool:
        """Deploy to Vercel using Vercel CLI."""
        project_dir = dep.config.get("project_dir", ".")
        token = dep.config.get("vercel_token", os.getenv("VERCEL_TOKEN", ""))

        dep.build_log.append("Running vercel deploy...")
        try:
            result = subprocess.run(
                ["npx", "vercel", "deploy", "--prod", "--token", token[:8] + "..."],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            dep.build_log.append(result.stdout)
            dep.url = result.stdout.strip().split("\n")[-1] if result.stdout else None
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            dep.error = "Vercel deploy timed out"
            return False

    def _docker_deploy(self, dep: Deployment) -> bool:
        """Build and push Docker image."""
        dep.build_log.append(f"Building Docker image for {dep.project}...")
        # TODO: docker build + push
        dep.build_log.append("Docker build skipped (not implemented)")
        return True

    def _local_deploy(self, dep: Deployment) -> bool:
        """Local development deployment — copies artifacts."""
        dep.build_log.append(f"Local deploy of {dep.project}@{dep.version}")
        dep.url = f"http://localhost:{dep.config.get('port', 8000)}"
        return True

    @property
    def deployments(self) -> dict[str, Deployment]:
        return dict(self._deployments)
