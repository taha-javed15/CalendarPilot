const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");

const composer = document.getElementById("composer");
const input = document.getElementById("input");
const sendButton = document.getElementById("send");

/* Templates */

const assistantTemplate =
    document.getElementById("assistant-message-template");

const userTemplate =
    document.getElementById("user-message-template");

const typingTemplate =
    document.getElementById("typing-template");

/* Keep one conversation */

const sessionId = crypto.randomUUID();

/* Request lock */

let waitingForResponse = false;

/* ==========================================================
   Auto Resize Textarea
========================================================== */

function resizeTextarea() {

    input.style.height = "auto";

    input.style.height =
        Math.min(input.scrollHeight, 180) + "px";

}

input.addEventListener("input", resizeTextarea);

/* ==========================================================
   Helpers
========================================================== */

function scrollToBottom() {

    messages.lastElementChild?.scrollIntoView({
        behavior: "smooth",
        block: "end"
    });

}

function hideWelcome() {

    if (!welcome.classList.contains("hidden")) {

        welcome.classList.add("hidden");

    }

}

function disableComposer() {

    waitingForResponse = true;

    input.disabled = true;

    sendButton.disabled = true;

}

function enableComposer() {

    waitingForResponse = false;

    input.disabled = false;

    sendButton.disabled = false;

    input.focus();

}

function renderMarkdown(bubbleEl, rawText) {
    // Re-parses and re-sanitizes on every update. For chat-length
    // messages this is cheap enough to do per chunk and keeps the
    // rendered markdown (bold, lists, etc.) correct throughout the
    // stream, rather than only being valid once the message is complete.
    bubbleEl.innerHTML = DOMPurify.sanitize(marked.parse(rawText));
}

/* ==========================================================
   Create Messages
========================================================== */

function createUserMessage(text) {

    const fragment =
        userTemplate.content.cloneNode(true);

    fragment.querySelector(".bubble").textContent = text;

    messages.appendChild(fragment);

    hideWelcome();

    scrollToBottom();

}

function createAssistantMessage(text) {

    const fragment =
        assistantTemplate.content.cloneNode(true);

    fragment.querySelector(".bubble").innerHTML = DOMPurify.sanitize(marked.parse(text));

    messages.appendChild(fragment);

    scrollToBottom();

    return messages.lastElementChild;

}

let typingElement = null;

function showTyping() {

    const fragment =
        typingTemplate.content.cloneNode(true);

    typingElement =
        fragment.firstElementChild;

    messages.appendChild(fragment);

    scrollToBottom();

}

function hideTyping() {

    if (typingElement) {

        typingElement?.remove();

        typingElement = null;

    }

}

/* ==========================================================
   Streaming Send (SSE via fetch)
========================================================== */

async function streamAssistantReply(message) {

    const response = await fetch("/chat/stream", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            message: message,
            session_id: sessionId
        })

    });

    if (!response.ok || !response.body) {
        throw new Error("Server returned an error.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";
    let accumulated = "";
    let bubbleEl = null;
    let sawAnyToken = false;

    while (true) {

        const { value, done } = await reader.read();

        if (done) {
            break;
        }

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by a blank line.
        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) !== -1) {

            const rawEvent = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);

            let eventType = "message";
            let dataLine = "";

            for (const line of rawEvent.split("\n")) {
                if (line.startsWith("event:")) {
                    eventType = line.slice(6).trim();
                } else if (line.startsWith("data:")) {
                    dataLine = line.slice(5).trim();
                }
            }

            if (!dataLine) {
                continue;
            }

            let payload;
            try {
                payload = JSON.parse(dataLine);
            } catch (e) {
                continue;
            }

            if (eventType === "done") {
                continue;
            }

            if (payload.error) {
                if (!bubbleEl) {
                    hideTyping();
                    bubbleEl = createAssistantMessage("");
                }
                accumulated = payload.error;
                renderMarkdown(bubbleEl.querySelector(".bubble"), accumulated);
                scrollToBottom();
                continue;
            }

            if (typeof payload.delta === "string") {
                if (!sawAnyToken) {
                    sawAnyToken = true;
                    hideTyping();
                    bubbleEl = createAssistantMessage("");
                }
                accumulated += payload.delta;
                renderMarkdown(bubbleEl.querySelector(".bubble"), accumulated);
                scrollToBottom();
            }
        }
    }

    // Edge case: the assistant's full reply was an empty string (e.g. a
    // malformed tool response that produced no text) - make sure the
    // user still sees *something* rather than a bubble that never
    // appeared.
    if (!bubbleEl) {
        hideTyping();
        createAssistantMessage("Sorry, I didn't get a response for that. Please try again.");
    }
}

/* ==========================================================
   Send Message
========================================================== */

async function sendMessage() {

    if (waitingForResponse) {
        return;
    }

    const message = input.value.trim();

    if (!message) {
        return;
    }

    createUserMessage(message);

    input.value = "";
    resizeTextarea();

    disableComposer();

    showTyping();

    try {

        await streamAssistantReply(message);

    }

    catch (error) {

        console.error(error);

        hideTyping();

        createAssistantMessage(
            "Sorry, something went wrong. Please try again."
        );

    }

    finally {

        enableComposer();

    }

}

/* ==========================================================
   Composer Submit
========================================================== */

composer.addEventListener("submit", function(event){

    event.preventDefault();

    sendMessage();

});

/* ==========================================================
   Keep Focus
========================================================== */

window.addEventListener("load", () => {

    resizeTextarea();

});

/* ==========================================================
   Keyboard Shortcuts
========================================================== */

input.addEventListener("keydown", function(event){

    if(event.key === "Enter" && !event.shiftKey){

        event.preventDefault();

        sendMessage();

    }

});

/* ==========================================================
   Escape Key
========================================================== */

document.addEventListener("keydown", function(event){

    if(event.key === "Escape"){

        input.blur();

    }

});

/* ==========================================================
   Prevent Empty Newlines
========================================================== */

input.addEventListener("paste", function(){

    setTimeout(resizeTextarea, 0);

});

/* ==========================================================
   Initial State
========================================================== */

resizeTextarea();

input.focus();

/* ==========================================================
   Nice UX
========================================================== */

document.addEventListener("visibilitychange", function(){

    if(document.visibilityState === "visible"){

        input.focus();

    }

});

/* ==========================================================
   Welcome Message (Optional)
========================================================== */

// Uncomment this if you want CalendarPilot to greet
// the user automatically when the page opens.

/*

setTimeout(() => {

    createAssistantMessage(
        "Hi! I'm CalendarPilot. I can create events, update meetings, check your availability, invite attendees, and manage your Google Calendar using natural language."
    );

}, 400);

*/

/* ==========================================================
   End
========================================================== */