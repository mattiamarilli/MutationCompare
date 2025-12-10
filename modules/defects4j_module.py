from utils import run_command
import subprocess

def defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
    """
    Checkout a specific Defects4J project and bug version.
    """
    checkout_command = f"defects4j checkout -p {project_id} -v {bug_id}{fixed_version} -w {working_dir}"
    stdout, stderr, returncode = run_command(checkout_command)

    if returncode != 0:
        print(f"Error during project checkout: {stderr}")
        return False

    return True


def defects4j_compile(working_dir):
    """
    Compile the Defects4J project inside the given working directory.
    """
    stdout, stderr, returncode = run_command("defects4j compile", cwd=working_dir)

    if returncode != 0:
        print(f"Error during project compilation: {stderr}")
        return False

    return True


def defects4j_test(working_dir):
    """
    Run the test suite using Defects4J.
    """
    stdout, stderr, returncode = run_command("defects4j test", cwd=working_dir)

    if returncode != 0:
        print(f"Error during project tests: {stderr}")
        return False

    return True


def defects4j_test_with_timeout(working_dir, timeout=30):
    """
    Run Defects4J tests with a timeout.
    Returns:
        "ok" if tests finish within the timeout,
        "timeout" if execution exceeds the allowed time.
    """
    try:
        subprocess.run(
            "defects4j test",
            shell=True,
            cwd=working_dir,
            timeout=timeout,
            capture_output=True, 
            text=True
        )
        return "ok"

    except subprocess.TimeoutExpired:
        return "timeout"

