from typing import Union


def extract_argument(text: str, enforce_digit: bool = False) -> Union[str, None]:
    args = text.strip().split(maxsplit=1)

    if len(args) < 2:
        return None

    argument = args[1].strip()
    return None if enforce_digit and not argument.isdigit() else argument
