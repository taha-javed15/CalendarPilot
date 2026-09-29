tools = [
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Use this tool to create an event on the user's Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "Start date and time in ISO 8601 format (e.g. 2026-07-18T14:00:00+05:30)."
                    },
                    "end": {
                        "type": "string",
                        "description": "End date and time in ISO 8601 format (e.g. 2026-07-18T14:00:00+05:30)."
                    },
                    "summary": {
                        "type": "string",
                        "description": "Title of the Calendar event."
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description, agenda, or notes for the event."
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional location for the event."
                    }
                },
                "required": [
                    "start",
                    "end",
                    "summary"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "Use this tool when the user asks about their schedule, meetings, appointments, or calendar events within a specific time period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "Start date and time in ISO 8601 format (e.g. 2026-07-18T14:00:00+05:30)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End date and time in ISO 8601 format (e.g. 2026-07-18T14:00:00+05:30)."
                    }
                },
                "required": [
                    "start_time",
                    "end_time"
                ]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "update_event",
        "description": "Update an existing Google Calendar event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event, e.g. 'dentist appointment', 'team meeting', 'lunch with Sarah'."
                },
                "search_start": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period (e.g. 'tomorrow', 'next week') to avoid matching events outside that window."
                },
                "search_end": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "summary": {
                    "type": "string",
                    "description": "New event title."
                },
                "description": {
                    "type": "string",
                    "description": "New event description, agenda, meeting notes, links, or any other details."
                },
                "start": {
                    "type": "string",
                    "description": "New start time in ISO 8601 format."
                },
                "end": {
                    "type": "string",
                    "description": "New end time in ISO 8601 format."
                },
                "location": {
                    "type": "string",
                    "description": "New meeting location."
                }
            },
            "required": [
                "event_query"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "delete_event",
        "description": "Delete a single existing Google Calendar event. Always asks for confirmation before deleting.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event, e.g. 'dentist appointment', 'team meeting', 'lunch with Sarah'."
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period to avoid matching events outside that window."
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                }
            },
            "required": [
                "event_query"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "batch_delete_events",
        "description": "Delete multiple Google Calendar events that match a query. Use this when the user wants to delete several events at once, e.g. 'delete all my meetings tomorrow' or 'cancel all gym sessions this week'. Always asks for confirmation before deleting.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to narrow the events, e.g. 'team meeting', 'gym session'. For broad requests like 'all events', 'all', or 'everything tomorrow', DO NOT provide this field at all - omit it entirely so every event in the given time range is matched. Only provide it when the user names a specific kind of event to delete among others (e.g. 'delete all my gym sessions this week' but leave other events alone)."
                },
                "start_time": {
                    "type": "string",
                    "description": "Start of the search window in ISO 8601 format. Highly recommended whenever the user mentions a time period to avoid deleting events outside the intended window."
                },
                "end_time": {
                    "type": "string",
                    "description": "End of the search window in ISO 8601 format. Highly recommended whenever the user mentions a time period."
                }
            },
            "required": []
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "find_free_time",
        "description": "Find available free time slots in the user's calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "string",
                    "description": "Start of the search range in ISO 8601 format."
                },
                "end_time": {
                    "type": "string",
                    "description": "End of the search range in ISO 8601 format."
                }
            },
            "required": [
                "start_time",
                "end_time"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "get_settings",
        "description": "Retrieve the user's CalendarPilot settings, including working hours, meeting defaults, daily briefing configuration, and time zone.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "update_settings",
        "description": "Update one or more CalendarPilot settings such as working hours, meeting defaults, daily briefing, or time zone.",
        "parameters": {
            "type": "object",
            "properties": {
                "working_hours_start": {
                    "type": "string",
                    "description": "Start of working hours in HH:MM format (e.g. '09:00')."
                },
                "working_hours_end": {
                    "type": "string",
                    "description": "End of working hours in HH:MM format (e.g. '17:00')."
                },
                "event_default_duration": {
                    "type": "integer",
                    "description": "Default meeting duration in minutes."
                },
                "event_default_reminder": {
                    "type": "integer",
                    "description": "Default reminder time in minutes before the meeting."
                },
                "daily_briefing_enabled": {
                    "type": "boolean",
                    "description": "Whether the daily agenda briefing is enabled."
                },
                "daily_briefing_time": {
                    "type": "string",
                    "description": "Time of day to send the daily briefing in HH:MM format."
                },
                "time_zone": {
                    "type": "string",
                    "description": "IANA time zone identifier, e.g. 'Asia/Kolkata' or 'America/New_York'."
                }
            }
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "suggest_alternative_times",
        "description": "Suggest alternative available meeting times within a given time range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "string",
                    "description": "Beginning of the search window in ISO 8601 format."
                },
                "end_time": {
                    "type": "string",
                    "description": "End of the search window in ISO 8601 format."
                },
                "max_suggestions": {
                    "type": "integer",
                    "description": "Maximum number of alternative time slots to return."
                }
            },
            "required": [
                "start_time",
                "end_time"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "find_best_event_time",
        "description": "Find the best available time slot for a calendar event within a given time range. The assistant considers the event type, available free time, and the user's working hours to recommend the most suitable slot.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "string",
                    "description": "Start of the search window in ISO 8601 format."
                },
                "end_time": {
                    "type": "string",
                    "description": "End of the search window in ISO 8601 format."
                },
                "event_summary": {
                    "type": "string",
                    "description": "Title or description of the calendar event, such as 'Gym', 'Lunch with Sarah', or 'Project meeting'."
                },
                "event_duration": {
                    "type": "integer",
                    "description": "Duration of the event in minutes. If omitted, the user's default event duration will be used."
                }
            },
            "required": [
                "start_time",
                "end_time",
                "event_summary"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "invite_attendees",
        "description": "Invite one or more attendees to an existing Google Calendar event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event, such as 'team meeting', 'dentist appointment', or 'lunch with Sarah'."
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "attendees": {
                    "type": "array",
                    "description": "List of attendee email addresses to invite.",
                    "items": {
                        "type": "string",
                        "description": "Attendee email address."
                    }
                }
            },
            "required": [
                "event_query",
                "attendees"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "update_attendees",
        "description": "Add attendees to or remove attendees from an existing Google Calendar event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event, such as 'team meeting', 'dentist appointment', or 'lunch with Sarah'."
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "add_attendees": {
                    "type": "array",
                    "description": "List of attendee email addresses to add.",
                    "items": {
                        "type": "string",
                        "description": "Attendee email address."
                    }
                },
                "remove_attendees": {
                    "type": "array",
                    "description": "List of attendee email addresses to remove.",
                    "items": {
                        "type": "string",
                        "description": "Attendee email address."
                    }
                }
            },
            "required": [
                "event_query"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "get_attendee_status",
        "description": "Get the RSVP status of attendees for a Google Calendar event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event, such as 'team meeting', 'dentist appointment', or 'lunch with Sarah'."
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                }
            },
            "required": [
                "event_query"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "get_attendees",
        "description": "Get the attendees of a Google Calendar event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event, such as 'team meeting', 'dentist appointment', or 'lunch with Sarah'."
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                }
            },
            "required": [
                "event_query"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "view_attendee_comments",
        "description": "View comments left by attendees for a Google Calendar event invitation.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event, such as 'team meeting', 'dentist appointment', or 'lunch with Sarah'."
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                }
            },
            "required": [
                "event_query"
            ]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "configure_reminders",
        "description": "Configure reminder settings for an existing Google Calendar event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event."
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "use_default": {
                    "type": "boolean",
                    "description": "Whether to use the calendar's default reminder settings."
                },
                "reminders": {
                    "type": "array",
                    "description": "Custom reminder overrides.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "string",
                                "enum": ["popup", "email"],
                                "description": "Reminder method."
                            },
                            "minutes": {
                                "type": "integer",
                                "description": "Minutes before the event."
                            }
                        },
                        "required": ["method", "minutes"]
                    }
                }
            },
            "required": ["event_query"]
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "get_event_details",
        "description": "Retrieve detailed information about a Google Calendar event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_query": {
                    "type": "string",
                    "description": "Natural language description used to identify the event, such as 'team meeting', 'dentist appointment', or 'lunch with Sarah'."
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start of a search window in ISO 8601 format. Use this when the user mentions a time period."
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end of a search window in ISO 8601 format. Use this when the user mentions a time period."
                }
            },
            "required": [
                "event_query"
            ]
        }
    }
    }
]