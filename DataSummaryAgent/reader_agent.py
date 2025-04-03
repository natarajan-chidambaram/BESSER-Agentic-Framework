import base64
import logging
import pymupdf

from besser.agent.core.agent import Agent
from besser.agent.core.file import File
from besser.agent.core.session import Session
from besser.agent.exceptions.logger import logger

# Configure the logging module to log messages to the console
logger.setLevel(logging.INFO)

# Create and provide a name for the agent 
agent = Agent('reader_agent')
# Load agent properties stored in the config file
agent.load_properties('../config.ini')
# Define the platform your agent will use
websocket_platform = agent.use_websocket_platform(use_ui=True)

# Define states present in the agent
initial_state = agent.new_state('initial_state', initial=True)
receive_doc_state = agent.new_state('receive_document_state')
awaiting_summary_state = agent.new_state('awaiting_summary_state')
send_summary_state = agent.new_state('send_summary_state')
final_state = agent.new_state('final_state')
exit_state = agent.new_state('exit_state')

# Provide intents for the states
yes_intent = agent.new_intent('yes_intent', [
    'yes',
])

no_intent = agent.new_intent('bad_intent', [
    'no',
])

# STATES BODIES' DEFINITION + TRANSITIONS
def initial_body(session: Session):
    websocket_platform.reply(session, "Hello, welcome to data summarisation agent. Upload your pdf document that needs to be summarised.")

def initial_fallback(session: Session):
    websocket_platform.reply(session, "Please, upload your pdf document before proceeding.")

initial_state.set_body(initial_body)
initial_state.when_file_received_go_to(receive_doc_state)
initial_state.set_fallback_body(initial_fallback)

def receive_doc_body(session: Session):
    # unsupported_file = False
    if session.file:
        # Receiving the document to be summarised
        file: File = session.file
        # Decode the base64 encoded file content and store it in the session
        # Decode base64 content
        pdf_data = base64.b64decode(file.base64)

        # Check if the file is a PDF and read its contents. If not display unsupported file type.
        if session.file.type == 'application/pdf':
            document = pymupdf.open(stream=pdf_data,filetype="pdf")
            text = "\n".join([page.get_text("text") for page in document])
        else:
            # unsupported_file = True
            text = "Unsupported file type. Please upload a PDF."
        session.set('document',text)
        session.file = None
    elif session.get('new_document'):
        session.set('document', session.get('new_document'))
    
    # if unsupported_file:
    websocket_platform.reply(session, "Thanks, I stored your PDF file in my database.")
    # websocket_platform.reply(session, session.get('document'))
    
    # return(unsupported_file)
    # websocket_platform.reply(session, session.get('code'))

# unsupported_file = receive_doc_state.set_body(receive_doc_body)
# print(unsupported_file)
# while(unsupported_file):
#     print(unsupported_file)
#     receive_doc_state.go_to(initial_state)
#     initial_state.when_file_received_go_to(receive_doc_state)
#     unsupported_file = receive_doc_state.set_body(receive_doc_body)
# receive_doc_state.go_to(awaiting_doc_state)

receive_doc_state.set_body(receive_doc_body)
receive_doc_state.go_to(awaiting_summary_state)

def awaiting_request_body(session: Session):
    session.delete('new_document')
    websocket_platform.reply(session, "How can I assist you?")

awaiting_summary_state.set_body(awaiting_request_body)
awaiting_summary_state.when_no_intent_matched_go_to(send_summary_state)

def send_request_body(session: Session):
    websocket_platform.reply(session, "Let's see what I can do...")
    session.send_message_to_websocket(
        url='ws://localhost:8011',
        message={
            "request": session.message,
            "document": session.get('document')
        }
    )

send_summary_state.set_body(send_request_body)
send_summary_state.when_no_intent_matched_go_to(final_state)

def final_body(session: Session):
    summary: str = session.message
    session.set('summary', summary)
    websocket_platform.reply(session, "Take a look at the summary")
    websocket_platform.reply(session, summary)
    websocket_platform.reply(session, "Do you want to continue?")
    websocket_platform.reply_options(session, ['Yes', 'No'])

def thank_you_body(session: Session):
    websocket_platform.reply(session, "Thank you for using BESSER Agentic Framework. Have a great day!")
    agent.stop()

final_state.set_body(final_body)
final_state.when_intent_matched_go_to(yes_intent, receive_doc_state)
final_state.when_intent_matched_go_to(no_intent, exit_state)

exit_state.set_body(thank_you_body)

# run the agent
if __name__ == '__main__':
    agent.run()