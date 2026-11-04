"""Which module handles which event. Order matters: mastery runs before revision, so the
revision schedule and the next question both see the updated knowledge state."""

from app.shared.consumers import Handler
from app.shared.events import EventType


def handlers_for(event_type: str) -> list[tuple[str, Handler]]:
    from app.modules.error_notebook import service as notebook
    from app.modules.knowledge_model import service as knowledge
    from app.modules.revision import service as revision

    table: dict[str, list[tuple[str, Handler]]] = {
        EventType.QUESTION_ANSWERED: [
            ("mastery", knowledge.on_question_answered),
            ("revision", revision.on_question_answered),
            ("error_notebook", notebook.on_question_answered),
        ],
    }
    return table.get(event_type, [])
