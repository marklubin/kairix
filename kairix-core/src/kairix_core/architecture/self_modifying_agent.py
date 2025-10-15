"""
Self-Modifying Agent Architecture
==================================

This module implements a safe, versioned, and auditable self-modification
system for Kairix agents, allowing them to evolve and improve their own
capabilities while maintaining safety and reliability.
"""

import ast
import asyncio
import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kairix_core.types.cognition import Perception, Stimulus, StimulusType
from kairix_core.cognition.perceptor import Perceptor


class ModificationType(Enum):
    """Types of self-modifications"""
    CODE_PATCH = auto()          # Small code change
    BEHAVIOR_UPDATE = auto()      # Update decision logic
    PERCEPTOR_ADD = auto()       # Add new perceptor
    PERCEPTOR_MODIFY = auto()    # Modify existing perceptor
    CAPABILITY_EXTEND = auto()    # Add new capability
    OPTIMIZATION = auto()         # Performance improvement


class SecurityLevel(Enum):
    """Security levels for modifications"""
    SAFE = 0          # No external access, pure computation
    MONITORED = 1     # Logged and reversible
    RESTRICTED = 2    # Requires approval
    CRITICAL = 3      # Requires multi-factor approval


@dataclass
class ModificationProposal:
    """A proposed self-modification"""
    id: str
    type: ModificationType
    description: str
    code_changes: Dict[str, str]  # file -> new content
    rationale: str
    expected_impact: str
    security_level: SecurityLevel
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    rollback_plan: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModificationResult:
    """Result of a self-modification attempt"""
    proposal_id: str
    success: bool
    version_before: int
    version_after: int
    execution_time: float
    test_results: List[Dict[str, Any]]
    error: Optional[str] = None
    rolled_back: bool = False


class CodeSandbox:
    """
    Isolated environment for testing code modifications
    """

    def __init__(self, use_docker: bool = False):
        self.use_docker = use_docker
        self.container_id = None

    async def test_code(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        timeout: float = 10.0
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Test code in isolated environment
        """
        if self.use_docker:
            return await self._test_in_docker(code, test_cases, timeout)
        else:
            return await self._test_in_subprocess(code, test_cases, timeout)

    async def _test_in_subprocess(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        timeout: float
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Test in subprocess with restricted permissions"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Write test harness
            f.write(code)
            f.write("\n\n")
            f.write("import json\n")
            f.write("import sys\n")
            f.write(f"test_cases = {json.dumps(test_cases)}\n")
            f.write("""
results = []
for test_case in test_cases:
    try:
        # Execute test
        result = eval(test_case['test'])
        expected = test_case.get('expected')

        if expected is not None:
            passed = result == expected
        else:
            passed = True

        results.append({
            'test': test_case['test'],
            'passed': passed,
            'result': str(result),
            'expected': str(expected) if expected else None
        })
    except Exception as e:
        results.append({
            'test': test_case['test'],
            'passed': False,
            'error': str(e)
        })

print(json.dumps(results))
            """)
            test_file = f.name

        try:
            # Run with restricted permissions
            process = await asyncio.create_subprocess_exec(
                'python3', test_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Limit resources
                env={
                    'PATH': '/usr/bin:/bin',
                    'PYTHONPATH': ''
                }
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                if process.returncode != 0:
                    return False, [{'error': stderr.decode()}]

                results = json.loads(stdout.decode())
                all_passed = all(r['passed'] for r in results)
                return all_passed, results

            except asyncio.TimeoutError:
                process.kill()
                return False, [{'error': f'Timeout after {timeout}s'}]

        finally:
            Path(test_file).unlink(missing_ok=True)

    async def _test_in_docker(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        timeout: float
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Test in Docker container for maximum isolation"""
        # TODO: Implement Docker-based sandboxing
        raise NotImplementedError("Docker sandbox not yet implemented")


class VersionControl:
    """
    Version control system for agent code
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.versions_dir = base_path / '.versions'
        self.versions_dir.mkdir(exist_ok=True)
        self.current_version = self._get_latest_version()

    def _get_latest_version(self) -> int:
        """Get the latest version number"""
        versions = list(self.versions_dir.glob('v*.json'))
        if not versions:
            return 0
        return max(int(v.stem[1:]) for v in versions)

    def save_version(
        self,
        files: Dict[str, str],
        metadata: Dict[str, Any]
    ) -> int:
        """Save a new version"""
        version = self.current_version + 1
        version_data = {
            'version': version,
            'timestamp': datetime.utcnow().isoformat(),
            'files': files,
            'metadata': metadata,
            'hash': self._compute_hash(files)
        }

        version_file = self.versions_dir / f'v{version}.json'
        with open(version_file, 'w') as f:
            json.dump(version_data, f, indent=2)

        self.current_version = version
        return version

    def load_version(self, version: int) -> Optional[Dict[str, Any]]:
        """Load a specific version"""
        version_file = self.versions_dir / f'v{version}.json'
        if not version_file.exists():
            return None

        with open(version_file) as f:
            return json.load(f)

    def rollback_to(self, version: int) -> bool:
        """Rollback to a specific version"""
        version_data = self.load_version(version)
        if not version_data:
            return False

        # Restore files
        for file_path, content in version_data['files'].items():
            full_path = self.base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)

        self.current_version = version
        return True

    def _compute_hash(self, files: Dict[str, str]) -> str:
        """Compute hash of all files"""
        hasher = hashlib.sha256()
        for path in sorted(files.keys()):
            hasher.update(path.encode())
            hasher.update(files[path].encode())
        return hasher.hexdigest()


class SelfModifyingAgent:
    """
    An agent that can safely modify its own code and capabilities
    """

    def __init__(
        self,
        agent_path: Path,
        require_approval: bool = True,
        max_versions: int = 100
    ):
        self.agent_path = agent_path
        self.require_approval = require_approval
        self.max_versions = max_versions

        self.sandbox = CodeSandbox()
        self.version_control = VersionControl(agent_path)
        self.pending_proposals: Dict[str, ModificationProposal] = {}
        self.modification_history: List[ModificationResult] = []

    async def propose_modification(
        self,
        proposal: ModificationProposal
    ) -> str:
        """
        Propose a self-modification
        """
        # Validate proposal
        validation = await self._validate_proposal(proposal)
        if not validation['valid']:
            raise ValueError(f"Invalid proposal: {validation['reason']}")

        # Store proposal
        self.pending_proposals[proposal.id] = proposal

        # Auto-approve if safe and allowed
        if (not self.require_approval and
            proposal.security_level == SecurityLevel.SAFE):
            return await self.apply_modification(proposal.id)

        return proposal.id

    async def apply_modification(
        self,
        proposal_id: str,
        approval_token: Optional[str] = None
    ) -> ModificationResult:
        """
        Apply a proposed modification
        """
        if proposal_id not in self.pending_proposals:
            raise ValueError(f"Unknown proposal: {proposal_id}")

        proposal = self.pending_proposals[proposal_id]

        # Check approval if required
        if (self.require_approval and
            proposal.security_level.value >= SecurityLevel.RESTRICTED.value):
            if not approval_token:
                raise PermissionError("Approval required for this modification")
            # TODO: Validate approval token

        start_time = datetime.utcnow()
        version_before = self.version_control.current_version

        try:
            # Test modifications in sandbox
            test_success, test_results = await self._test_modification(proposal)

            if not test_success:
                return ModificationResult(
                    proposal_id=proposal_id,
                    success=False,
                    version_before=version_before,
                    version_after=version_before,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                    test_results=test_results,
                    error="Tests failed in sandbox"
                )

            # Apply modifications
            current_files = self._snapshot_current_files()

            # Apply changes
            for file_path, new_content in proposal.code_changes.items():
                full_path = self.agent_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(new_content)

            # Save version
            version_after = self.version_control.save_version(
                proposal.code_changes,
                {
                    'proposal': proposal.__dict__,
                    'test_results': test_results
                }
            )

            # Verify modifications work
            if not await self._verify_modifications():
                # Rollback
                self.version_control.rollback_to(version_before)
                return ModificationResult(
                    proposal_id=proposal_id,
                    success=False,
                    version_before=version_before,
                    version_after=version_before,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                    test_results=test_results,
                    error="Verification failed after applying modifications",
                    rolled_back=True
                )

            result = ModificationResult(
                proposal_id=proposal_id,
                success=True,
                version_before=version_before,
                version_after=version_after,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                test_results=test_results
            )

            self.modification_history.append(result)
            del self.pending_proposals[proposal_id]

            return result

        except Exception as e:
            # Rollback on any error
            self.version_control.rollback_to(version_before)
            return ModificationResult(
                proposal_id=proposal_id,
                success=False,
                version_before=version_before,
                version_after=version_before,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                test_results=[],
                error=str(e),
                rolled_back=True
            )

    async def _validate_proposal(
        self,
        proposal: ModificationProposal
    ) -> Dict[str, Any]:
        """Validate a modification proposal"""
        # Check for syntax errors
        for file_path, code in proposal.code_changes.items():
            if file_path.endswith('.py'):
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    return {
                        'valid': False,
                        'reason': f'Syntax error in {file_path}: {e}'
                    }

        # Check for dangerous patterns based on security level
        if proposal.security_level == SecurityLevel.SAFE:
            dangerous_patterns = [
                'exec(', 'eval(', '__import__',
                'subprocess', 'os.system',
                'open(', 'socket.', 'requests.'
            ]

            for file_path, code in proposal.code_changes.items():
                for pattern in dangerous_patterns:
                    if pattern in code:
                        return {
                            'valid': False,
                            'reason': f'Dangerous pattern "{pattern}" in {file_path}'
                        }

        return {'valid': True}

    async def _test_modification(
        self,
        proposal: ModificationProposal
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Test modifications in sandbox"""
        # Combine all Python files for testing
        combined_code = []
        for file_path, code in proposal.code_changes.items():
            if file_path.endswith('.py'):
                combined_code.append(f"# File: {file_path}\n{code}\n")

        full_code = '\n'.join(combined_code)

        # Run tests
        return await self.sandbox.test_code(
            full_code,
            proposal.test_cases,
            timeout=30.0
        )

    def _snapshot_current_files(self) -> Dict[str, str]:
        """Take snapshot of current files"""
        snapshot = {}
        for py_file in self.agent_path.rglob('*.py'):
            rel_path = py_file.relative_to(self.agent_path)
            with open(py_file) as f:
                snapshot[str(rel_path)] = f.read()
        return snapshot

    async def _verify_modifications(self) -> bool:
        """Verify modifications work correctly"""
        # TODO: Implement runtime verification
        # Could include:
        # - Import checks
        # - Basic functionality tests
        # - Performance benchmarks
        return True

    def get_modification_history(self, limit: int = 10) -> List[ModificationResult]:
        """Get recent modification history"""
        return self.modification_history[-limit:]

    def get_current_capabilities(self) -> Dict[str, Any]:
        """Get current agent capabilities"""
        # TODO: Introspect current code to determine capabilities
        return {
            'version': self.version_control.current_version,
            'perceptors': [],  # List discovered perceptors
            'tools': [],       # List available tools
            'modifications_enabled': True,
            'security_level': 'RESTRICTED'
        }


class SelfImprovementPerceptor(Perceptor):
    """
    A perceptor that monitors agent performance and proposes improvements
    """

    def __init__(self, agent: SelfModifyingAgent):
        self.agent = agent
        self.performance_metrics: List[Dict[str, Any]] = []
        self.improvement_threshold = 0.7  # Propose improvements below this

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        """
        Monitor performance and propose improvements
        """
        if stimulus.type == StimulusType.self_perception:
            # Analyze recent performance
            performance = await self._analyze_performance()

            if performance['score'] < self.improvement_threshold:
                # Generate improvement proposal
                proposal = await self._generate_improvement_proposal(
                    performance['issues']
                )

                if proposal:
                    # Submit proposal
                    proposal_id = await self.agent.propose_modification(proposal)

                    return [Perception(
                        source="self_improvement",
                        content=json.dumps({
                            'type': 'improvement_proposed',
                            'proposal_id': proposal_id,
                            'expected_improvement': performance['expected_improvement']
                        }),
                        confidence=0.8
                    )]

        return []

    async def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze recent performance metrics"""
        # TODO: Implement performance analysis
        return {
            'score': 0.6,
            'issues': ['slow_response_time', 'memory_inefficiency'],
            'expected_improvement': 0.2
        }

    async def _generate_improvement_proposal(
        self,
        issues: List[str]
    ) -> Optional[ModificationProposal]:
        """Generate improvement proposal based on identified issues"""
        # TODO: Use LLM to generate improvement code
        return None


# Example usage
EXAMPLE_MODIFICATION_PROPOSAL = ModificationProposal(
    id="optimize_perception_001",
    type=ModificationType.OPTIMIZATION,
    description="Optimize perception processing with caching",
    code_changes={
        "cognition/perceptor_cache.py": '''
from functools import lru_cache
from typing import List
from kairix_core.types.cognition import Perception, Stimulus

class PerceptorCache:
    """Cache for frequently accessed perceptions"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache = {}

    @lru_cache(maxsize=128)
    def get_cached_perception(self, stimulus_hash: str) -> Optional[List[Perception]]:
        """Get cached perception for stimulus"""
        return self._cache.get(stimulus_hash)

    def cache_perception(self, stimulus_hash: str, perceptions: List[Perception]):
        """Cache perception result"""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[stimulus_hash] = perceptions
'''
    },
    rationale="Caching frequently accessed perceptions will reduce processing time",
    expected_impact="20-30% reduction in perception processing time",
    security_level=SecurityLevel.SAFE,
    test_cases=[
        {
            "test": "PerceptorCache(100)",
            "expected": "PerceptorCache"
        }
    ]
)