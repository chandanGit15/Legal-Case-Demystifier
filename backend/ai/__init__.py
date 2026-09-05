"""Centralized AI service layer.

Every AI feature in the application must call Gemini through this package.
Exports the public API used by routes and services.
"""
from .service import (ai_available, analyze_case_overview, analyze_case_risks,
                      analyze_document, analyze_negotiation_prep,
                      answer_case_question, assess_risks, assistant_chat, b64encode,
                      build_case_context, compare_scenarios, detect_information_gaps,
                      detect_legal_issues, evaluate_negotiation, explain_simply,
                      explain_term, extract_deadline_dates, extract_timeline_events,
                      generate_action_plan, generate_negotiation_message,
                      generate_scenario, image_payload, negotiation_practice,
                      simulation_reply, summarize_case)

__all__ = [
    "ai_available",
    "analyze_case_overview",
    "analyze_case_risks",
    "analyze_document",
    "analyze_negotiation_prep",
    "answer_case_question",
    "assess_risks",
    "assistant_chat",
    "b64encode",
    "build_case_context",
    "compare_scenarios",
    "detect_information_gaps",
    "detect_legal_issues",
    "evaluate_negotiation",
    "explain_simply",
    "explain_term",
    "extract_deadline_dates",
    "extract_timeline_events",
    "generate_action_plan",
    "generate_negotiation_message",
    "generate_scenario",
    "image_payload",
    "negotiation_practice",
    "simulation_reply",
    "summarize_case",
]