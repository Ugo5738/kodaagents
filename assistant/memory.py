from datetime import datetime


class BaseMemory:
    def __init__(self):
        self.full_conversation_history = []  # Store full details including timestamps
        self.openai_conversation_history = []  # Store only role and content
        self.unanswered_questions = 0  # Count number of unanswered questions
        self.votes = {}
        self.session_start_time = None  # Time when the session starts
        self.session_end_time = None  # Time when the session ends

    def add_message(self, role, content, **kwargs):
        # Add to full conversation history
        message_id = kwargs.get("message_id", None)
        duration = kwargs.get("duration", None)
        self.full_conversation_history.append(
            {
                "role": role,
                "content": content,
                "message_id": message_id,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Add to OpenAI-specific conversation history
        self.openai_conversation_history.append({"role": role, "content": content})

    def upvote(self, message_id):
        self.votes[message_id] = self.votes.get(message_id, 0) + 1

    def downvote(self, message_id):
        self.votes[message_id] = self.votes.get(message_id, 0) - 1

    def increment_unanswered_questions(self):
        self.unanswered_questions += 1

    def get_history(self):
        return self.full_conversation_history

    def get_openai_history(self):
        return self.openai_conversation_history

    def get_votes(self):
        return self.votes

    def to_dict(self):
        return {
            "full_conversation_history": self.full_conversation_history,
            "openai_conversation_history": self.openai_conversation_history,
            "unanswered_questions": self.unanswered_questions,
            "votes": self.votes,
            "session_start_time": self.session_start_time,
            "session_end_time": self.session_end_time,
        }
