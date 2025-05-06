import subprocess
import typer

app = typer.Typer()


@app.command()
def submit() -> None:
    try:
        result = subprocess.run(
            ["git", "branchless", "query", "main() | stack() & branches()"],
            capture_output=True,
            text=True,
            check=True,
        )
        branches_to_submit = result.stdout.strip().splitlines()
        # TODO: Do something with branches_to_submit
        print(f"Branches to submit: {branches_to_submit}")  # Placeholder
    except subprocess.CalledProcessError as e:
        print(f"Error executing git command: {e}")
        # Handle error appropriately
        return
    except FileNotFoundError:
        print("Error: git command not found. Is git installed and in your PATH?")
        # Handle error appropriately
        return
    pass


def main():
    typer.run(app)
