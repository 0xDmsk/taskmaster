from xml.etree import ElementTree as ET

from skills.reporting import _rewrite_document_xml_markdown


def _document_xml(text: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr>
        <w:rPr>
          <w:rFonts w:ascii="Trebuchet MS" w:hAnsi="Trebuchet MS"/>
        </w:rPr>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Trebuchet MS" w:hAnsi="Trebuchet MS"/>
        </w:rPr>
        <w:t xml:space="preserve">{text}</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>
""".encode()


def _text_values(xml: bytes) -> list[str]:
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    return [node.text or "" for node in root.findall(".//w:t", ns)]


def test_rewrite_document_xml_markdown_formats_inline_and_fenced_code():
    xml = _document_xml(
        "Send `loginContextToken`.\n"
        "```python\n"
        "# capture the value\n"
        'value = "abc123"\n'
        "print(value)\n"
        "```\n"
        "Observe the response."
    )

    rewritten, changed = _rewrite_document_xml_markdown(xml)

    assert changed is True
    assert "```" not in rewritten.decode()
    assert "Roboto Mono" in rewritten.decode()
    assert "<w:tbl>" in rewritten.decode()
    assert 'w:fill="F6F8FA"' in rewritten.decode()
    assert 'w:val="single"' in rewritten.decode()
    assert 'w:color w:val="188038"' in rewritten.decode()
    assert 'w:color w:val="6A737D"' in rewritten.decode()
    assert 'w:color w:val="0A3069"' in rewritten.decode()
    assert 'w:color w:val="0550AE"' in rewritten.decode()
    assert 'w:sz w:val="18"' in rewritten.decode()
    all_text = "".join(_text_values(rewritten))
    assert "Send loginContextToken." in all_text
    assert "# capture the value" in all_text
    assert 'value = "abc123"' in all_text
    assert "print(value)" in all_text
    assert "Observe the response." in all_text


def test_rewrite_document_xml_markdown_leaves_plain_xml_unchanged():
    xml = _document_xml("Plain report prose without markdown.")

    rewritten, changed = _rewrite_document_xml_markdown(xml)

    assert changed is False
    assert rewritten == xml


def _root(xml: bytes) -> ET.Element:
    return ET.fromstring(xml)


_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def test_indented_block_becomes_a_code_table():
    # CommonMark treats a >=4-space-indented run as a code block. Findings are
    # routinely written that way rather than with ``` fences.
    text = (
        "Settings read from the console:&#10;&#10;"
        "    Unconfigured third-party apps    Allow any&#10;"
        "    Internal apps                    Trust internal&#10;&#10;"
        "Prose resumes here."
    )
    xml, changed = _rewrite_document_xml_markdown(_document_xml(text))
    assert changed
    root = _root(xml)
    tables = root.findall(".//w:tbl", _NS)
    assert len(tables) == 1
    fonts = tables[0].findall(".//w:rFonts", _NS)
    assert any(f.get(f"{{{_NS['w']}}}ascii") == "Roboto Mono" for f in fonts)
    assert "Prose resumes here." in _text_values(xml)


def test_pipe_table_becomes_a_word_table_with_header_row():
    text = (
        "| Credential | Result |&#10;"
        "| :---- | :---- |&#10;"
        "| Access token | 401 |&#10;"
        "| Refresh token | invalid_grant |"
    )
    xml, changed = _rewrite_document_xml_markdown(_document_xml(text))
    assert changed
    root = _root(xml)
    tables = root.findall(".//w:tbl", _NS)
    assert len(tables) == 1
    rows = tables[0].findall("w:tr", _NS)
    assert len(rows) == 3  # delimiter row is dropped
    assert rows[0].find(".//w:tblHeader", _NS) is not None
    values = _text_values(xml)
    assert "Credential" in values and "invalid_grant" in values


def test_list_items_get_a_bullet_and_an_indent():
    text = "- first item&#10;- second item"
    xml, changed = _rewrite_document_xml_markdown(_document_xml(text))
    assert changed
    root = _root(xml)
    paragraphs = root.findall(".//w:p", _NS)
    indented = [p for p in paragraphs if p.find("w:pPr/w:ind", _NS) is not None]
    assert len(indented) == 2
    assert "• " in _text_values(xml)


def test_bold_span_produces_a_bold_run():
    xml, changed = _rewrite_document_xml_markdown(_document_xml("a **loud** claim&#10;x"))
    assert changed
    root = _root(xml)
    bold_runs = [r for r in root.findall(".//w:r", _NS) if r.find("w:rPr/w:b", _NS) is not None]
    assert len(bold_runs) == 1
    assert bold_runs[0].find("w:t", _NS).text == "loud"


def test_paragraph_spacing_is_injected_when_the_template_supplies_none():
    xml, changed = _rewrite_document_xml_markdown(_document_xml("one&#10;&#10;two"))
    assert changed
    root = _root(xml)
    spacings = root.findall(".//w:p/w:pPr/w:spacing", _NS)
    assert spacings, "generated paragraphs must carry w:after so prose does not run together"
    assert any(s.get(f"{{{_NS['w']}}}after") == "160" for s in spacings)
