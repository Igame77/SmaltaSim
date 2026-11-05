import pytest
from core.quiz_engine import QuizBank, QuizSession, QuizResult

def test_quiz_bank_tests_exist():
    tests = QuizBank.get_all_tests()
    assert "vsp01_bereza" in tests
    assert "vsp01_rtr" in tests
    assert "vsp02_fasol" in tests
    assert "vsp02_sorbtia" in tests
    assert "vsp02_geran_siren" in tests
    assert "vsp03_smalta" in tests
    assert "vsp03_azalia" in tests
    assert "vsp_comprehensive" in tests

    for t_id, t_data in tests.items():
        assert len(t_data["questions"]) >= 2
        for q in t_data["questions"]:
            assert len(q.options) == 4
            assert 0 <= q.correct_idx < 4
            assert q.text != ""
            assert q.explanation != ""

def test_quiz_session_answering_and_grading():
    session = QuizSession("vsp02_fasol", {"name": "Иванов И.И.", "group": "ВУЦ-101", "variant": 2})
    assert session.total_questions == 5
    assert session.current_idx == 0

    # Answer all questions correctly
    for i, q in enumerate(session.questions):
        session.current_idx = i
        session.select_answer(q.correct_idx)

    result = session.finish_quiz()
    assert result.total_questions == 5
    assert result.correct_answers == 5
    assert result.score_percent == 100.0
    assert result.grade == 5
    assert result.grade_text == "Отлично"

def test_quiz_grading_thresholds():
    session = QuizSession("vsp01_bereza", {"name": "Петров П.П.", "group": "ВУЦ-102", "variant": 1})
    total = session.total_questions
    # Answer none correctly
    for i in range(total):
        session.current_idx = i
        session.select_answer((session.questions[i].correct_idx + 1) % 4)

    res_fail = session.finish_quiz()
    assert res_fail.correct_answers == 0
    assert res_fail.grade == 2
    assert res_fail.grade_text == "Неудовлетворительно"

def test_quiz_navigation():
    session = QuizSession("vsp03_smalta")
    assert session.current_idx == 0
    assert session.next_question() is True
    assert session.current_idx == 1
    assert session.prev_question() is True
    assert session.current_idx == 0
    assert session.prev_question() is False
