from mcp_server.utils.tool_result_logging import format_tool_result_for_log


def test_format_tool_result_for_log_truncates_by_default():
    result = {"courses": [{"course_code": "CSC 126", "sections": [{"section": "01"}]}]}

    rendered = format_tool_result_for_log(result, max_chars=40, full=False)

    assert rendered.endswith("...")
    assert len(rendered) == 43


def test_format_tool_result_for_log_can_emit_full_payload():
    result = {"courses": [{"course_code": "CSC 126", "sections": [{"section": "01"}]}]}

    rendered = format_tool_result_for_log(result, max_chars=10, full=True)

    assert rendered == str(result)
