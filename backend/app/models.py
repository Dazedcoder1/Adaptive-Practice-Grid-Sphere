"""Import every module's models so Alembic autogenerate sees all tables."""

from app.modules.academic import models as _academic  # noqa: F401
from app.modules.adaptive import models as _adaptive  # noqa: F401
from app.modules.administration import models as _administration  # noqa: F401
from app.modules.ai_tutor import models as _ai_tutor  # noqa: F401
from app.modules.analytics import models as _analytics  # noqa: F401
from app.modules.assessment import models as _assessment  # noqa: F401
from app.modules.audit import models as _audit  # noqa: F401
from app.modules.curriculum import models as _curriculum  # noqa: F401
from app.modules.error_notebook import models as _error_notebook  # noqa: F401
from app.modules.gamification import models as _gamification  # noqa: F401
from app.modules.identity import models as _identity  # noqa: F401
from app.modules.knowledge_model import models as _knowledge_model  # noqa: F401
from app.modules.learning_content import models as _learning_content  # noqa: F401
from app.modules.notifications import models as _notifications  # noqa: F401
from app.modules.practice import models as _practice  # noqa: F401
from app.modules.question_bank import models as _question_bank  # noqa: F401
from app.modules.rag import models as _rag  # noqa: F401
from app.modules.revision import models as _revision  # noqa: F401
from app.modules.security import models as _security  # noqa: F401
from app.modules.users import models as _users  # noqa: F401
from app.shared import events as _events  # noqa: F401
