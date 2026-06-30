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
