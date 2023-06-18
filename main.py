import playwright
from playwright.sync_api import Page, expect, sync_playwright
import json
from time import sleep
from lwe import ApiBackend
from lwe.core.config import Config
from lwe.core.template import TemplateManager
import re

GPT_CONFIG_DIR = "/home/user/.config/chatgpt-wrapper"
GPT_DATA_DIR = "/home/user/.local/share/chatgpt-wrapper"
GPT_PROFILE = "interpretor"
GPT_MODEL = "gpt-4"

class GPTError(RuntimeError):
    """Raised when the conversation leaves strict mode."""
    pass

class ThreadProcessingError(RuntimeError):
    """Raised any message processing (Playwright or internal logic) fails."""
    pass

class SendingError(RuntimeError):
    """Raised when sending a message fails."""
    pass

def read_thread(page):
    incoming_msgs = page.locator("div.full-container.end-of-cluster.incoming.ng-star-inserted gv-annotation.content.ng-star-inserted")
    # print(f"Unfiltered incoming messages {incoming_msgs.count()}")
    incoming=[]
    for i in range(incoming_msgs.count()):
        msg = incoming_msgs.nth(i).inner_text()
        incoming.append(msg)

    outgoing_msgs = page.locator("div.full-container.end-of-cluster.outgoing.ng-star-inserted gv-annotation.content.ng-star-inserted")
    # print(f"Unfiltered outgoing messages {outgoing_msgs.count()}")
    outgoing=[]
    for i in range(outgoing_msgs.count()):
        msg = outgoing_msgs.nth(i).inner_text()
        if not re.match('^((Me)|(You))> .*', msg):
            outgoing.append(msg)
    return incoming, outgoing

def filter_new_mgs(old_msgs, new_msgs):
    if not new_msgs:
        return []

    try:
        i = old_msgs.index(new_msgs[0])
    except:
        print(f"New message {new_msgs[0]} not in old messages")
        i = 0

    print("Found first new msg index", i)
    msgs = []
    while i < len(new_msgs):
        if i >= len(old_msgs):
            msgs.append(new_msgs[i])
        elif new_msgs[i] != old_msgs[i]:
            print(f"Unexpected mismatch at {i} new={new_msgs} old={old_msgs}")
            msgs.append(new_msgs[i])
        i = i + 1
    return msgs

class Interpretor:
    def __init__(self, playwright):
        # Define the bot handles.
        self.gpt_config = Config(config_dir=GPT_CONFIG_DIR, data_dir=GPT_DATA_DIR, profile=GPT_PROFILE)
        self.gpt = ApiBackend(self.gpt_config)
        self.gpt.load_user(1)
        self.templates = TemplateManager(self.gpt_config)

        self.browser = playwright.firefox.launch(headless=False)
        self.context = self.browser.new_context()
        self.incoming = []
        self.outgoing = []
        try:
            with open('cookies.json', 'r', encoding='utf-8') as f:
                self.context.add_cookies(json.load(f))
        except RuntimeError:
            print("Cookies not found")
            pass

    def translate(self, prefix, msg):
        success, response, message = self.gpt.ask(f"{msg}")
        if success:
            print(f"Translation:\n{prefix}> {response}")
            return f"{prefix}> {response}"
        else:
            raise GPTError(message)

    def watch(self, page):
        """Polls for new messages and yields the translations"""
        while True:
            try:
                incoming, outgoing = read_thread(page)
                print(f"Collected messages from UI incoming={len(incoming)} outgoing={len(outgoing)}")
                new_msgs = filter_new_mgs(self.incoming, incoming)
                if new_msgs:
                    print(f"Found {len(new_msgs)} new incoming messages to translate")
                self.incoming.clear()
                self.incoming.extend(incoming)
                for msg in new_msgs:
                    yield self.translate("You", msg)

                new_msgs = filter_new_mgs(self.outgoing, outgoing)
                if new_msgs:
                    print(f"Found {len(new_msgs)} new outgoing messages to translate")
                self.outgoing.clear()
                self.outgoing.extend(outgoing)
                for msg in new_msgs:
                    yield self.translate("Me", msg)
            except RuntimeError as err:
               print(f"Aborted iteration on unexpected error: {err}")

            sleep(1)

    def acquire_conversation(self, force_new=False):
        """Switch the gpt handle to a newly acquired conversation"""
        if force_new:
            self.gpt.new_conversation()

        c = self.gpt.create_new_conversation_if_needed(None, title=f"Google Voice Interpreter")
        print(f"In conversation id={c.id} title={c.title}")
        self.gpt.set_model("gpt-4")
        self.templates.load_templates()
        prompt = self.templates.build_message_from_template("mandarin.md")[0]
        print("Initializing with template:\n", prompt)
        success, response, message = self.gpt.ask(f"{prompt}")
        if success:
            print(f"Init response:\n{response}")
            return c
        else:
            raise GPTError(message)

    def run(self):
        page = self.context.new_page()
        page.goto("https://voice.google.com/u/0/messages")

        cookies = self.context.cookies()
        print("Found cookies", cookies)
        with open('cookies.json', 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=4)

        # Wait for five minutes
        print("Log in if necessary then select a message thread; waiting for UI components to be visible")
        msg_box = page.get_by_placeholder("Type a message")
        msg_box.wait_for(state='visible', timeout=300000)
        send_btn = page.get_by_label("Send message")
        send_btn.wait_for(state='visible', timeout=300000)

        print("Message thread UI ready; acquiring GPT interpreter conversation")
        c = self.acquire_conversation()

        # Print existing messages in thread without translating them.
        print("Collecting contents of the message thread:")
        self.incoming, self.outgoing = read_thread(page)
        for msg in self.incoming:
            print(f"You> {msg}")
        for msg in self.outgoing:
            print(f"Me> {msg}")

        print("Watching UI for new messages to translate")
        for response in self.watch(page):
            print("Sending translation message")
            msg_box.fill(response)
            sleep(1)
            send_btn.click()
            tokens = self.gpt.get_conversation_token_count(c.id)
            print(f"Sent response; tokens used in conversation {tokens}/{self.gpt.max_submission_tokens}")
            if self.gpt.max_submission_tokens - tokens < 100:
                print("Creating a new conversation; context will be loss")
                self.acquire_conversation(force_new=True)


with sync_playwright() as playwright:
    Interpretor(playwright).run()
