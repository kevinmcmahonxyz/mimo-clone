import docker
import tempfile
import os

from backend.config import settings


def build_code_with_mocked_inputs(code: str, mock_inputs: list[str]) -> str:
    """Wrap user code to mock input() calls with predefined values."""
    if not mock_inputs:
        return code

    inputs_repr = repr(mock_inputs)
    wrapper = f"""import builtins
_mock_inputs = {inputs_repr}
_input_index = 0

def _mock_input(prompt=''):
    global _input_index
    if prompt:
        print(prompt, end='')
    if _input_index < len(_mock_inputs):
        val = _mock_inputs[_input_index]
        _input_index += 1
        return val
    return ''

builtins.input = _mock_input

"""
    return wrapper + code


def execute_code(code: str, mock_inputs: list[str] | None = None) -> dict:
    """Execute Python code in a Docker sandbox and return the output."""
    if mock_inputs is None:
        mock_inputs = []

    # Seed random for deterministic output (projects using random module)
    seeded_code = "import random; random.seed(42)\n" + code
    wrapped_code = build_code_with_mocked_inputs(seeded_code, mock_inputs)

    # Try Docker sandbox first, fall back to local execution
    try:
        client = docker.from_env()
        client.images.get(settings.sandbox_image)
    except (docker.errors.DockerException, docker.errors.ImageNotFound):
        return _execute_locally(wrapped_code)

    # Write code to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    ) as f:
        f.write(wrapped_code)
        code_path = f.name

    try:
        result = client.containers.run(
            settings.sandbox_image,
            command=["python", "/code/script.py"],
            volumes={code_path: {"bind": "/code/script.py", "mode": "ro"}},
            network_disabled=True,
            mem_limit=settings.sandbox_memory_limit,
            cpu_period=settings.sandbox_cpu_period,
            cpu_quota=settings.sandbox_cpu_quota,
            remove=True,
            stderr=True,
            stdout=True,
        )

        output = result.decode("utf-8") if isinstance(result, bytes) else result
        return {"success": True, "output": output, "error": None}

    except docker.errors.ContainerError as e:
        stderr = e.stderr.decode("utf-8") if e.stderr else str(e)
        return {"success": False, "output": "", "error": _clean_traceback(stderr)}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}
    finally:
        os.unlink(code_path)


def _execute_locally(code: str) -> dict:
    """Fallback execution without Docker (for development)."""
    import subprocess

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    ) as f:
        f.write(code)
        code_path = f.name

    try:
        result = subprocess.run(
            ["python3", code_path],
            capture_output=True,
            text=True,
            timeout=settings.sandbox_timeout,
        )

        if result.returncode == 0:
            return {"success": True, "output": result.stdout, "error": None}
        else:
            return {
                "success": False,
                "output": result.stdout,
                "error": _clean_traceback(result.stderr),
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Code execution timed out. Check for infinite loops.",
        }
    finally:
        os.unlink(code_path)


def _clean_traceback(error: str) -> str:
    """Remove sandbox file paths from tracebacks to show cleaner errors."""
    lines = error.strip().split("\n")
    cleaned = []
    for line in lines:
        line = line.replace("/code/script.py", "your_code.py")
        # Skip the mock input wrapper lines from traceback
        if "_mock_input" in line or "_input_index" in line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)
