# Google Calendar Summarizer - Complete Documentation

## Overview
A conversational AI agent that fetches your Google Calendar events and provides intelligent summaries and answers about your schedule using OpenAI's GPT model with conversation memory.

---

## 🏗️ Workflow Architecture

```
┌─────────────────────────────┐
│  When chat message received │  (Chat Trigger)
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│     Get many events         │  (Google Calendar)
│  - Fetches next 7 days      │
│  - Ordered by start time    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Format Events          │  (Code Node)
│  - Formats dates/times      │
│  - Adds location info       │
│  - Creates text summary     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        AI Agent             │
│  ┌───────────────────────┐  │
│  │ OpenAI Chat Model     │  │
│  │ (gpt-4o-mini)         │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │ Window Buffer Memory  │  │
│  │ (Session-based)       │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

---

## 📊 Node Details

### 1. When chat message received (Chat Trigger)

**Type:** `@n8n/n8n-nodes-langchain.chatTrigger`  
**Version:** 1.1  
**Webhook ID:** `calendar-chat-simple`

**Purpose:**
- Provides a built-in chat interface
- Handles user messages
- Manages session IDs for conversation memory
- No configuration needed

**Output:**
```json
{
  "chatInput": "What's on my schedule today?",
  "sessionId": "d5734f00-a14a-4949-a7d4-04fa2e2ea16e",
  "action": "sendMessage"
}
```

---

### 2. Get many events (Google Calendar)

**Type:** `n8n-nodes-base.googleCalendar`  
**Version:** 1.2  
**Operation:** Get All

**Configuration:**
- **Calendar:** `teomastro1999@gmail.com` (your calendar)
- **Always Output Data:** ✅ Enabled (important!)
- **Return All:** ❌ Disabled
- **Limit:** 50 events

**Options:**
- **timeMin:** `{{ $now.startOf('day').toISO() }}`  
  Starts from today at midnight
- **timeMax:** `{{ $now.plus({days: 7}).toISO() }}`  
  Ends 7 days from now
- **singleEvents:** `true`  
  Expands recurring events into individual instances
- **orderBy:** `startTime`  
  Orders events chronologically

**Why "Always Output Data" is Important:**
- Even if there are no events, the workflow continues
- Prevents workflow from stopping when calendar is empty
- Format Events node can handle empty data gracefully

**Sample Output:**
```json
[
  {
    "summary": "Team Meeting",
    "start": {
      "dateTime": "2025-11-06T15:00:00+02:00"
    },
    "end": {
      "dateTime": "2025-11-06T17:00:00+02:00"
    },
    "location": "https://zoom.us/j/12345",
    "description": "Weekly team sync",
    "attendees": [
      { "email": "colleague@example.com" }
    ]
  }
]
```

---

### 3. Format Events (Code Node)

**Type:** `n8n-nodes-base.code`  
**Version:** 2  
**Language:** JavaScript

**Purpose:**
- Transforms raw calendar API data into human-readable format
- Handles both timed events and all-day events
- Combines calendar summary with original chat input
- Provides fallback for empty calendars

**Code Logic:**

```javascript
// 1. Get all events from previous node
const events = $input.all();

// 2. Handle empty calendar
if (!events || events.length === 0) {
  return {
    json: {
      chatInput: $('When chat message received').item.json.chatInput,
      calendarSummary: "You have no events scheduled in the next 7 days."
    }
  };
}

// 3. Format each event
const formattedEvents = events.map((item, i) => {
  const event = item.json;
  
  let timeStr = '';
  
  // Handle timed events
  if (event.start?.dateTime) {
    const start = new Date(event.start.dateTime);
    const end = new Date(event.end.dateTime);
    const startStr = start.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
    const endStr = end.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
    timeStr = `${startStr} - ${endStr}`;
  } 
  // Handle all-day events
  else if (event.start?.date) {
    const date = new Date(event.start.date);
    timeStr = date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    }) + ' (All day)';
  }
  
  // Build event line
  let eventLine = `${i + 1}. ${timeStr}: ${event.summary || 'Untitled'}`;
  
  // Add location if present
  if (event.location) {
    eventLine += ` @ ${event.location}`;
  }
  
  return eventLine;
}).join('\n\n');

// 4. Create summary
const summary = `Here are your calendar events for the next 7 days (${events.length} total):\n\n${formattedEvents}`;

// 5. Get original chat input
const chatInput = $('When chat message received').item.json.chatInput;

// 6. Return combined data
return {
  json: {
    chatInput: chatInput,
    calendarSummary: summary
  }
};
```

**Output Example:**
```json
{
  "chatInput": "What's on my schedule?",
  "calendarSummary": "Here are your calendar events for the next 7 days (1 total):\n\n1. Thu, Nov 6, 03:00 PM - 05:00 PM: O4A Hands-On Modelling @ https://zoom.us/..."
}
```

---

### 4. AI Agent

**Type:** `@n8n/n8n-nodes-langchain.agent`  
**Version:** 1.7

**System Prompt:**
```
You are a helpful calendar assistant.

Today's date: {{ $now.toFormat('yyyy-MM-dd') }}
Current time: {{ $now.toFormat('HH:mm') }}

The user's calendar events have already been fetched and formatted. Use this information to answer their questions:

{{ $json.calendarSummary }}

Provide clear, helpful responses about their schedule. Group events by day when it makes sense. Highlight important details like location or timing conflicts.
```

**Key Features:**
- **Dynamic Date Context:** Knows current date and time
- **Pre-loaded Calendar Data:** Events are in the prompt (no tools needed)
- **Flexible Responses:** Can answer various schedule-related questions
- **Context-Aware:** Groups, filters, and highlights based on query

**Connected Components:**
- **Language Model:** OpenAI Chat Model (GPT-4o-mini)
- **Memory:** Window Buffer Memory (session-based)

---

### 5. OpenAI Chat Model

**Type:** `@n8n/n8n-nodes-langchain.lmChatOpenAi`  
**Version:** 1  
**Model:** Default (gpt-4o-mini)

**Configuration:**
- **Credentials:** OpenAI API account
- **Options:** Default settings
  - Temperature: 0.7 (balanced creativity)
  - Max tokens: Default

**Model Characteristics:**
- **Fast:** Quick response times
- **Cost-effective:** Lower cost than GPT-4
- **Capable:** Good for conversational tasks and summarization
- **Context window:** 128k tokens (more than enough for calendar data)

**Alternative Models:**
- `gpt-4o` - More capable, slower, more expensive
- `gpt-3.5-turbo` - Faster, cheaper, less capable

---

### 6. Window Buffer Memory

**Type:** `@n8n/n8n-nodes-langchain.memoryBufferWindow`  
**Version:** 1.2

**Configuration:**
- **Session ID Type:** Custom Key
- **Session Key:** `{{ $('When chat message received').item.json.sessionId }}`

**Purpose:**
- Maintains conversation history within a session
- Allows follow-up questions without repeating context
- Each chat session has its own isolated memory
- Automatically managed by Chat Trigger

**How It Works:**
```
User: "What's on my schedule today?"
Agent: "You have 1 event: Team Meeting at 3 PM"

User: "What about the location?"
Agent: [remembers previous context] "The Team Meeting is at https://zoom.us/..."
```

**Memory Window:**
- Keeps recent conversation turns
- Older messages are automatically dropped
- Prevents context window overflow
- Default window size is sufficient for typical conversations

---

## 🚀 How to Use

### Setup

1. **Import Workflow**
   - Import the JSON file into n8n

2. **Configure Credentials**
   - **Google Calendar:** OAuth2 authentication
   - **OpenAI:** API key from platform.openai.com

3. **Activate Workflow**
   - Toggle "Active" switch ON

4. **Access Chat Interface**
   - Click "When chat message received" node
   - Click "Test Chat" button
   - Or copy the production URL for external access
