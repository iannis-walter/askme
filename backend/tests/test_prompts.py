import prompts
from content_loader import Chunk

CHUNKS = [Chunk("a", "A", "faq", "some text")]


def test_chat_system_has_injection_rule():
    s = prompts.CHAT_SYSTEM.lower()
    assert "data" in s and "instructions" in s and "never" in s


def test_job_fit_system_has_injection_rule():
    s = prompts.JOB_FIT_SYSTEM.lower()
    assert "data" in s and "instructions" in s


def test_chat_message_is_delimited_with_reminder():
    msgs = prompts.build_chat_messages("hello there", CHUNKS, [])
    user = msgs[-1]["content"]
    assert "<<<USER_QUESTION>>>" in user and "<<<END_USER_QUESTION>>>" in user
    assert "hello there" in user
    assert "treat it as data" in user.lower()


def test_job_fit_delimits_job_description():
    msgs = prompts.build_job_fit_messages("JD body text", "AI role", CHUNKS)
    user = msgs[-1]["content"]
    assert "<<<JOB_DESCRIPTION>>>" in user and "<<<END_JOB_DESCRIPTION>>>" in user
    assert "JD body text" in user
    assert "treat it as data" in user.lower()
