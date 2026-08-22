#!/usr/bin/env python3

import json
import signal

from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ollama_client import ask_ollama, unload_model
from searxng_manager import ensure_searxng_running, stop_searxng
from web_tools import web_search
from file_search import read_file, read_dir

console = Console()

display_history = []


def redraw_display(signum, frame):
    console.clear()

    console.print("Bob the Garuda Hyprland AI assistant")
    console.print("Type 'exit' to quit.\n")

    for item in display_history:
        if item["type"] == "bob":
            console.print(
                Panel(
                    Markdown(item["content"]),
                    title="[bold cyan]Bob[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )
            console.print()
            if {"type": "source"} in display_history:
                console.print("[bold yellow]Sources used:[/bold yellow]")
        elif item["type"] == "source":
            console.print(
                f"  • [link={item['url']}]{item['title']}[/link]\n"
                f"    [dim]{item['url']}[/dim]"
            )
        elif item["type"] == "user":
            console.print(f"[bold green]You:[/bold green] {item['content']}")
            console.print()
        elif item["type"] == "tool":
            if item["name"] == "web_search":
                console.print(
                    f"[dim yellow]Searched web:[/dim yellow] {item['content']}"
                )
            elif item["name"] == "read_file":
                console.print(f"[dim green]Read file[/dim green] {item['content']}")

            elif item["name"] == "read_dir":
                console.print(
                    f"[dim green]Read directory[/dim green] {item['content']}"
                )
    console.print("[bold green]You:[/bold green] ", end="")


signal.signal(signal.SIGWINCH, redraw_display)

# Ollama receives this schema so the model knows it can request
# a web search and what argument the tool expects.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet for current or external information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to send to SearXNG.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file on the user's computer."
                "Use and absolute or valid relative file path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The path of the file to read, for example "
                            "/home/kai/.config/hypr/hyprland.conf."
                        ),
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_dir",
            "description": (
                "List files inside a directory on the user's computer. "
                "Use this to discover file locations before reading a file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The directory path to inspect, for example "
                            "/home/kai/.config/hypr."
                        ),
                    }
                },
                "required": ["query"],
            },
        },
    },
]


OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "bob:latest"


def cleanup():
    """Remove the SearXNG container and clear Ollama VRAM when the script exits."""
    unload_model()
    stop_searxng()


def web_search_helper(query, sources_used):
    display_history.append(
        {"type": "tool", "name": "web_search", "content": f"{query}"}
    )
    try:
        with console.status(
            f"[bold yellow]Searching web: {query}[/bold yellow]",
            spinner="dots",
            spinner_style="yellow",
        ):
            result = web_search(query)

        for source in json.loads(result):
            source_entry = {
                "title": source.get("title", ""),
                "url": source.get("url", ""),
            }

            if source_entry not in sources_used:
                sources_used.append(source_entry)
        console.print(f"[dim yellow]Searched web:[/dim yellow] {query}")

    except Exception as e:
        console.print(f"[bold red]Web search error:[/bold red] {e}")

        result = json.dumps({"error": f"Web search failed: {e}"})

    return result


def read_file_helper(query):
    display_history.append({"type": "tool", "name": "read_file", "content": f"{query}"})
    try:
        with console.status(
            f"[bold green]Reading File:[/bold green] {query}",
            spinner="dots",
            spinner_style="green",
        ):
            result = json.dumps(read_file(query))
        console.print(f"[dim green]Read file[/dim green] {query}")
    except Exception as e:
        console.print(f"[bold red]File read error[/bold red] {e}")

        result = json.dumps({"error": f"File read failed: {e}"})

    return result


def read_dir_helper(query):
    display_history.append({"type": "tool", "name": "read_dir", "content": f"{query}"})
    try:
        with console.status(
            f"[bold green]Reading Directory:[/bold green] {query}",
            spinner="dots",
            spinner_style="green",
        ):
            result = json.dumps(read_dir(query))
        console.print(f"[dim green]Read Directory[/dim green] {query}")
    except Exception as e:
        console.print(f"[bold red]Directory read error[/bold red] {e}")

        result = json.dumps({"error": f"Directory read failed: {e}"})

    return result


def main():
    ensure_searxng_running()
    current_date = datetime.now().strftime("%B %d, %Y")

    # This system message gives the local model today's date and tells it when
    # it should prefer live web data over potentially stale training data.
    messages = [
        {
            "role": "system",
            "content": (
                f"Today's date is {current_date}. "
                "When the user asks for current, latest, recent, or time-sensitive "
                "information, search the web and use the current date when forming "
                "search queries. Do not assume your training-data date is current."
                "You also have the ability to read the users files from their computer."
                "Instead of assuming where file locations are, use your file read and directory read"
                "tools to find the actual location."
            ),
        }
    ]

    print("Bob the Garuda Hyprland AI assistant")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            prompt = console.input("[bold green]You:[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if prompt.strip().lower() in {"exit", "quit"}:
            break

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        display_history.append(
            {
                "type": "user",
                "content": prompt,
            }
        )

        sources_used = []

        # One user prompt can require several Ollama turns:
        #   1. Bob requests a tool.
        #   2. Python runs that tool and appends its result.
        #   3. Bob receives the result and either answers or requests another tool.
        max_searches = 15  # Maximum consecutive web seaches
        completed_queries = set()  # Ensure unique searches each cycle
        while True:
            with console.status(
                "[bold cyan]Bob is thinking...[/bold cyan]",
                spinner="dots",
                spinner_style="cyan",
            ) as status:
                response = ask_ollama(messages, TOOLS)

            message = response["message"]
            messages.append(message)

            tool_calls = message.get("tool_calls", [])

            # No requested tools means Bob has produced the final answer.
            if not tool_calls:
                display_history.append(
                    {"type": "bob", "content": message.get("content", "")}
                )
                console.print(
                    Panel(
                        Markdown(message.get("content", "")),
                        title="[bold cyan]Bob[/bold cyan]",
                        border_style="cyan",
                        padding=(1, 2),
                    )
                )

                # If Bob used web search during this question, show the pages
                # that were returned by SearXNG underneath the final response.
                if sources_used:
                    console.print("[bold yellow]Sources used:[/bold yellow]")

                    for source in sources_used:
                        display_history.append(
                            {
                                "type": "source",
                                "url": f"{source['url']}",
                                "title": f"{source['title']}",
                            }
                        )
                        console.print(
                            f"  • [link={source['url']}]{source['title']}[/link]\n"
                            f"    [dim]{source['url']}[/dim]"
                        )
                # lazy \n
                console.print()
                break

            # Execute each tool call, then append its output to conversation
            # history so Ollama can use it on the next pass through the loop.
            for call in tool_calls:
                function = call["function"]

                if function["name"] not in ("web_search", "read_file", "read_dir"):
                    continue

                arguments = function.get("arguments", {})

                # Depending on the model/Ollama version, tool arguments may
                # arrive as a parsed dict or as a JSON-encoded string.
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)

                query = arguments.get("query", "")

                # Bob wants to search the web!

                if function["name"] == "web_search":
                    # Unique check
                    if query in completed_queries:
                        continue

                    completed_queries.add(query)
                    if len(completed_queries) >= max_searches:
                        break

                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": "web_search",
                            "content": web_search_helper(query, sources_used),
                        }
                    )

                # Bob wants to read a file!

                if function["name"] == "read_file":
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": "read_file",
                            "content": read_file_helper(query),
                        }
                    )

                # Bob wants to read a directory!

                if function["name"] == "read_dir":
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": "read_dir",
                            "content": read_dir_helper(query),
                        }
                    )
    cleanup()


if __name__ == "__main__":
    main()
