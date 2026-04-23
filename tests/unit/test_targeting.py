import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from targeting import normalize_taskmaster_host, targets_match


def test_normalize_taskmaster_host_rewrites_loopback_values():
    assert normalize_taskmaster_host("127.0.0.1") == "host.docker.internal"
    assert normalize_taskmaster_host("localhost") == "host.docker.internal"


def test_targets_match_exact_url():
    assert targets_match("https://www.example.com/path", "https://www.example.com/path")


def test_targets_match_hostname_scope_to_url_target():
    assert targets_match("www.example.com", "https://www.example.com/path")


def test_targets_match_exact_path_when_both_include_one():
    assert targets_match("https://www.example.com/path", "https://www.example.com/path/")
    assert not targets_match("https://www.example.com/path", "https://www.example.com/other")

