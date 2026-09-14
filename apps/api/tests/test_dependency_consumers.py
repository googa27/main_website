"""Real IDNA and Alembic consumers, using public inputs and no external I/O."""

import ast
import socket
from importlib.metadata import distribution
from importlib.resources import files
from pathlib import Path

import httpx
import idna
import pytest
from alembic.script import ScriptDirectory
from email_validator import EmailNotValidError, validate_email
from pydantic import ValidationError

from app.schemas.contact import ContactCreate


@pytest.fixture(autouse=True)
def prohibit_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refused(*args: object, **kwargs: object) -> None:
        raise AssertionError("Dependency consumer controls must not use the network")

    monkeypatch.setattr(socket, "getaddrinfo", refused)
    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(socket.socket, "connect_ex", refused)


@pytest.mark.parametrize(
    "address,normalized,ascii_address",
    [
        ("person@example.com", "person@example.com", "person@example.com"),
        ("person@bücher.de", "person@bücher.de", "person@xn--bcher-kva.de"),
        ("person@xn--bcher-kva.de", "person@bücher.de", "person@xn--bcher-kva.de"),
    ],
)
def test_contact_and_email_validator_normalize_real_idna_domains(
    address: str, normalized: str, ascii_address: str
) -> None:
    validated = validate_email(address, check_deliverability=False)
    assert validated.normalized == normalized
    assert validated.ascii_email == ascii_address
    contact = ContactCreate(name="Synthetic", email=address, message="Local probe")
    assert contact.email == normalized


@pytest.mark.parametrize("domain", ["☃.de", "xn---bbk.de"])
def test_contact_and_email_validator_refuse_invalid_or_noncanonical_domains(
    domain: str,
) -> None:
    address = f"person@{domain}"
    with pytest.raises(EmailNotValidError):
        validate_email(address, check_deliverability=False)
    with pytest.raises(ValidationError):
        ContactCreate(name="Synthetic", email=address, message="Local probe")


@pytest.mark.parametrize(
    "host,ascii_host",
    [("example.com", b"example.com"), ("bücher.de", b"xn--bcher-kva.de")],
)
def test_runtime_httpx_prepares_ascii_and_unicode_hosts_without_sending(
    host: str, ascii_host: bytes
) -> None:
    request = httpx.Request("GET", f"https://{host}/users/synthetic/repos")
    assert request.url.raw_host == ascii_host
    assert request.headers["host"] == ascii_host.decode("ascii")
    assert httpx.__name__ == "httpx"  # Runtime client, not Starlette's httpx2.


@pytest.mark.parametrize("host", ["☃.de", "xn---bbk.bücher.de"])
def test_runtime_httpx_refuses_invalid_idna_hosts(host: str) -> None:
    # HTTPX bypasses IDNA for wholly ASCII hosts; the second input deliberately
    # includes a Unicode label so its actual IDNA path checks the entire host.
    with pytest.raises(httpx.InvalidURL):
        httpx.Request("GET", f"https://{host}/")


def test_idna_distinguishes_canonical_alabel_from_ambiguous_punycode() -> None:
    # Exact upstream IDNA 3.19 regression: both spellings decode to the same
    # U-label under permissive Punycode, but only one is a canonical A-label.
    assert idna.ulabel("xn--bbk") == "ま"
    assert idna.encode("xn--bbk.de") == b"xn--bbk.de"
    with pytest.raises(idna.IDNAError):
        idna.decode("xn---bbk.de")


@pytest.mark.parametrize("template_owner", ["installed_alembic", "repository"])
def test_alembic_renders_real_revision_templates_without_database(
    tmp_path: Path, template_owner: str
) -> None:
    if template_owner == "installed_alembic":
        template = (
            files("alembic").joinpath("templates/generic/script.py.mako").read_bytes()
        )
    else:
        template = (Path(__file__).parents[1] / "alembic/script.py.mako").read_bytes()
    (tmp_path / "script.py.mako").write_bytes(template)
    (tmp_path / "versions").mkdir()
    scripts = ScriptDirectory(str(tmp_path))
    assert not scripts.hooks
    # No env.py or database URL exists. No autogeneration or upgrade is invoked.
    revision = scripts.generate_revision(
        "144a",
        "synthetic dependency compatibility",
        head="base",
        imports="",
        upgrades='result = "upgrade-control"',
        downgrades='result = "downgrade-control"',
    )
    assert revision is not None
    assert revision.revision == "144a"
    assert revision.down_revision is None
    output = Path(revision.path)
    assert output.is_relative_to(tmp_path)
    rendered = output.read_text()
    parsed = ast.parse(rendered)
    functions = {
        node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)
    }
    for name, sentinel in (
        ("upgrade", "upgrade-control"),
        ("downgrade", "downgrade-control"),
    ):
        assert name in functions
        assert any(
            isinstance(node, ast.Constant) and node.value == sentinel
            for node in ast.walk(functions[name])
        )
    assert "${" not in rendered
    assert not (tmp_path / "env.py").exists()


def test_mako_distribution_does_not_own_stray_tools_package() -> None:
    owned = distribution("Mako").files
    assert owned is not None
    assert any(path.parts[0] == "mako" for path in owned)
    assert not any(
        path.parts[0] == "tools" or str(path) == "tools.py" for path in owned
    )
