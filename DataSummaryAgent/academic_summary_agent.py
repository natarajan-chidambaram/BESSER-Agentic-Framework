import logging
import os

from dotenv import load_dotenv

from besser.agent.core.agent import Agent
from besser.agent.core.session import Session
from besser.agent.exceptions.logger import logger
from besser.agent.nlp.llm.llm_openai_api import LLMOpenAI
from besser.agent.platforms.websocket import WEBSOCKET_PORT

# Configure the logging module to log messages to the console
logger.setLevel(logging.INFO)

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
# Create and provide a name for the agent 
agent = Agent('summary_agent')
# Load agent properties stored in the config file
agent.load_properties('../config.ini')
agent.set_property(WEBSOCKET_PORT, 8011)
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
generate_summary_state = agent.new_state('generate_summary_state')
update_summary_state = agent.new_state('update_summary_state')
reply_summary_state = agent.new_state('reply_summary_state')

# intents
ok_intent = agent.new_intent('yes_intent', [
    'ok',
])

# STATES BODIES' DEFINITION + TRANSITIONS
initial_state.when_no_intent_matched_go_to(generate_summary_state)

def generate_summary_body(session: Session):
    message = session.message
    summary: str = gpt.predict(
        message=f"You are expert in summarizing research based texts. Given the following document and requirement:\n\n"
                f"{message['document']}\n\n"
                f"{message['request']}\n\n"
                f"Provide this summary from academic researcher's perspective."
        )
    session.set('summary', summary)
    session.send_message_to_websocket(
        url='ws://localhost:8013',
        message=summary
    )

generate_summary_state.set_body(generate_summary_body)
generate_summary_state.when_intent_matched_go_to(ok_intent, reply_summary_state)
generate_summary_state.when_no_intent_matched_go_to(update_summary_state)

def update_summary_body(session: Session):
    issues: str = session.message
    summary: str = gpt.predict(
        message=f'Given the following text:\n\n'
                f'{session.get("summary")}\n\n'
                f'Update it based on the following corrected text:\n\n'
                f'{issues}'
    )
    session.set('summary', summary)
    session.send_message_to_websocket(
        url='ws://localhost:8013',
        message=summary
    )

update_summary_state.set_body(update_summary_body)
update_summary_state.when_intent_matched_go_to(ok_intent, reply_summary_state)
update_summary_state.when_no_intent_matched_go_to(update_summary_state)

def reply_summary_body(session: Session):
    websocket_platform.reply(session, session.get('summary'))

reply_summary_state.set_body(reply_summary_body)
reply_summary_state.go_to(initial_state)


# RUN APPLICATION

if __name__ == '__main__':
    agent.run()