def test_version_import():
    from aiblock_mcp.__about__ import __version__

    assert isinstance(__version__, str) and len(__version__) > 0


