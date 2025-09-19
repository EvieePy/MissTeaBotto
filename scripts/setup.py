from __future__ import annotations

import pathlib
import platform
import subprocess
import sys
import sysconfig
from collections.abc import Callable
from functools import partial
from typing import Any, Protocol, TypeVar


VT = TypeVar("VT", covariant=True)
type ValidT = list[str] | str | Callable[..., Any]


BOOL_MAPPING: dict[str, bool] = {
    "y": True,
    "n": False,
    "1": True,
    "0": False,
    "yes": True,
    "no": False,
    "t": True,
    "f": False,
    "true": True,
    "false": False,
}


class QuestionT(Protocol):
    def __call__(
        self, val: str, /, valid: ValidT, *, strict: bool = False, converter: ConverterT[VT] | None = None
    ) -> VT | str: ...


class ConverterT(Protocol[VT]):
    def __call__(self, inp: str) -> VT: ...


class BoolConverter(ConverterT[bool | None]):
    def __call__(self, inp: str) -> bool | None:
        return BOOL_MAPPING.get(inp.lower())


def validate(inp: str | object, /, *, original: str, valid: ValidT, strict: bool = False) -> bool:
    if original.lower() == "quit":
        return sys.exit(0)

    if callable(valid):
        return valid(inp)

    if isinstance(valid, str):
        result = original.lower() == valid.lower() if not strict else original == valid
        if result is False:
            raise ValueError

        return result

    assert isinstance(valid, list)
    if inp not in valid:
        raise ValueError

    return True


def question(val: str, /, valid: ValidT, *, strict: bool = False, converter: ConverterT[VT] | None = None) -> Any:
    while True:
        original: str = input(val)
        converted: VT | str = converter(original) if converter else original

        try:
            validate(converted, original=original, valid=valid, strict=strict)
        except Exception:
            print(f"{original} is not a valid answer: Please try again or type 'Quit' to exit.", end="\n\n")
            continue

        return converted


def question_wrapper(question: partial[QuestionT], *, expected: Any) -> Any:
    while True:
        result = question()

        if type(result) == expected or isinstance(result, expected):
            return result


def is_in_venv() -> bool:
    return sys.prefix != sys.base_prefix


def install(exe: pathlib.Path, starlette: bool | None = False) -> None:
    reqs = pathlib.Path.cwd() / "requirements.txt"
    subprocess.call([exe, "-m", "pip", "install", "-r", reqs, "--upgrade", "--no-cache"])


def is_free_threaded() -> bool:
    return not sys._is_gil_enabled() or sysconfig.get_config_var("Py_GIL_DISABLED")


def create_venv() -> pathlib.Path | None:
    # Create the venv...
    subprocess.call([sys.executable, "-m", "venv", ".venv"])
    system = platform.system()

    if system == "Windows":
        exe = pathlib.Path(".venv") / "Scripts" / "python.exe"
    elif system in ["Darwin", "Linux"]:
        exe = pathlib.Path(".venv") / "bin" / "python"
    else:
        print(
            "Unsupported operating system... Skipping package installation. Please manually install required packages.",
            end="\n\n",
        )
        return

    print("Successfully created virtual environment!", end="\n\n")
    return exe


def create() -> None:
    exe = pathlib.Path(sys.executable)

    if not is_in_venv():
        q = partial(
            question,
            "No Virtual Envionment found: Would you like to create a venv? ",
            converter=BoolConverter(),
            valid=bool,
            strict=True,
        )
        result = question_wrapper(q, expected=bool)

        if result:
            exe = create_venv()

    q = partial(
        question,
        "Would you like to install dependencies and requirements? ",
        converter=BoolConverter(),
        valid=bool,
        strict=True,
    )
    result = question_wrapper(q, expected=bool)

    if result and exe:
        install(exe)


def configs() -> None: ...


def main() -> None:
    create()
    configs()


if __name__ == "__main__":
    if is_free_threaded():
        raise RuntimeError(
            "This application does not currently support free-threaded versions of Python. Please run again with free-threading disabled."
        )

    main()
