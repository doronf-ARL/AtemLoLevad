from __future__ import annotations


class GenerationService:
    def generate(self, caregiver_message: str, action: str, merged_state: dict, knowledge: dict, micro_question: str | None) -> str:
        playbooks = knowledge["playbooks"]
        primary_playbook = playbooks[0] if playbooks else None
        opening = "What you are describing sounds like acute overload, not something to push through right now."

        if action == "ground":
            response = (
                "Keep your voice low and brief. "
                "Stay nearby, reduce noise, and give one simple anchor such as: "
                '"You are here with me, you are safe right now, let\'s just slow the breathing."'
            )
        elif action == "reduce_pressure":
            response = (
                "Step back from questions for the moment. "
                "Aim for presence over explanation, and offer one small next step like water, sitting down, or a quieter room."
            )
        elif action == "set_boundary":
            response = (
                "Keep the boundary short and calm. "
                "You can say that you want to stay supportive, and you will keep talking once the tone is safer and slower."
            )
        elif action == "escalate":
            response = (
                "This is a point to involve outside help now. "
                "If there is any immediate safety risk, contact emergency support or the treating clinician right away and stay with him if you can do so safely."
            )
        else:
            response = "Start with validation and one simple step rather than trying to solve the whole episode."

        if primary_playbook and primary_playbook.do_items:
            response = f"{response} Focus first on {primary_playbook.do_items[0].lower()}."

        if micro_question:
            return f"{opening} {response} {micro_question}"
        return f"{opening} {response}"
