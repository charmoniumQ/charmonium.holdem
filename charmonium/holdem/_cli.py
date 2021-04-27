import click


from . import _lib as lib

@click.command()
def main() -> None:
    """CLI for charmonium.holdem."""
    # print(lib.threes())
    print(lib.create_ranking())


main()
