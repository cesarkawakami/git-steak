import typer

app = typer.Typer()


@app.command()
def submit() -> None:
    # Let's start by creating a list of the branches to submit by calling `git branchless query 'main() | stack() & branches()'` ai!
    pass


def main():
    typer.run(app)
