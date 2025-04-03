import logging
import os

from dotenv import load_dotenv
from besser.agent.core.agent import Agent
from besser.agent.core.session import Session
from besser.agent.exceptions.logger import logger
from besser.agent.nlp.llm.llm_openai_api import LLMOpenAI
from besser.agent.platforms.websocket import WEBSOCKET_PORT

# Configure the logging module (optional)
logger.setLevel(logging.INFO)

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
# Create the agent
agent = Agent('reviewer_agent')
# Load agent properties stored in a dedicated file
agent.load_properties('../config.ini')
agent.set_property(WEBSOCKET_PORT, 8013)
# Define the platform your agent will use
websocket_platform = agent.use_websocket_platform(use_ui=False)

# Create the LLM
gpt = LLMOpenAI(
    agent=agent,
    name='gpt-4o-mini',
    parameters={},
    num_previous_messages=10
)

# states
initial_state = agent.new_state('initial_state', initial=True)
summary_review_state = agent.new_state('summary_review_state')

# intents
issues_intent = agent.new_intent('new_function_intent', [
    'issues'
])

ok_intent = agent.new_intent('yes_intent', [
    'ok',
])


# STATES BODIES' DEFINITION + TRANSITIONS

initial_state.when_no_intent_matched_go_to(summary_review_state)


def summary_review_body(session: Session):
    summary: str = session.message
    answer: str = gpt.predict(
        message=f"You are an expert in identifying grammatical errors and mistakes in text. Given the following text, try to find if there are mistakes like typos and grammatical errors.\n"
                f"If you think there is no mistake, just reply 'ok'.\n\n"
                f"{summary}"
    )
    websocket_platform.reply(session, answer)


summary_review_state.set_body(summary_review_body)
summary_review_state.go_to(initial_state)

# RUN APPLICATION

if __name__ == '__main__':
    agent.run()