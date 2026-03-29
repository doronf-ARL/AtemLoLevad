from sqlmodel import Session, SQLModel, create_engine

from app.db.models import Playbook
from app.domain.services.retrieval import RetrievalService


def test_retrieval_ranks_overlap_highest():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Playbook(title="Best", summary="", tags=["ground", "hyperarousal", "loud_noise_trigger"], applies_when=["hyperarousal"], do_items=[], dont_items=[], micro_questions=[], contraindications=[]))
        session.add(Playbook(title="Weaker", summary="", tags=["validate"], applies_when=["withdrawal"], do_items=[], dont_items=[], micro_questions=[], contraindications=[]))
        session.commit()
        service = RetrievalService()
        result = service.retrieve(session, "ground", {"patient_states": [{"label": "hyperarousal"}], "caregiver_states": [], "triggers": [{"label": "loud_noise_trigger"}]})
        assert result["playbooks"][0].title == "Best"
