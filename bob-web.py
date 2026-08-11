#!/usr/bin/env python3

import json
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ollama_client import ask_ollama, unload_model
from searxng_manager import ensure_searxng_running, stop_searxng
from web_tools import TOOLS, web_search

console = Console()

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "bob:latest"

def cleanup():
    """Remove the SearXNG container and clear Ollama VRAM when the script exits."""
    unload_model()
    stop_searxng()


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

        messages.append({
            "role": "user",
            "content": prompt,
        })

        sources_used = []

        # One user prompt can require several Ollama turns:
        #   1. Bob requests a tool.
        #   2. Python runs that tool and appends its result.
        #   3. Bob receives the result and either answers or requests another tool.
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

            if tool_calls:
                status.update(
                    "[bold yellow]Bob is thinking... Searching network...[/bold yellow]"
                )

            # No requested tools means Bob has produced the final answer.
            if not tool_calls:
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
                        console.print(
                            f"  • [link={source['url']}]{source['title']}[/link]\n"
                            f"    [dim]{source['url']}[/dim]"
                        )
                #lazy \n
                console.print()
                break

            # Execute each tool call, then append its output to conversation
            # history so Ollama can use it on the next pass through the loop.
            for call in tool_calls:
                function = call["function"]

                if function["name"] != "web_search":
                    continue

                arguments = function.get("arguments", {})

                # Depending on the model/Ollama version, tool arguments may
                # arrive as a parsed dict or as a JSON-encoded string.
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)

                query = arguments.get("query", "")

                try:
                    with console.status(
                        f"[bold yellow]Searching web: {query}[/bold yellow]",
                        spinner="dots",
                        spinner_style="yellow",
                    ):
                        result = web_search(query)

                    # Add sources used at the bottom of results for double checking answers
                    for source in json.loads(result):
                        source_entry = {
                            "title": source.get("title", ""),
                            "url": source.get("url", ""),
                        }

                        # Prevent duplicate links from appearing if multiple searches
                        # return the same page.
                        if source_entry not in sources_used:
                            sources_used.append(source_entry)

                    # Persist the attempted query in terminal history after the
                    # spinner disappears so the user can see what Bob searched.
                    console.print(f"[dim yellow]Searched web:[/dim yellow] {query}")

                except Exception as error:
                    console.print(f"[bold red]Web search error:[/bold red] {error}")

                    # Feed the failure back to the model as a normal tool result
                    # instead of crashing the whole chat session.
                    result = json.dumps({
                        "error": f"Web search failed: {error}"
                    })

                messages.append({
                    "role": "tool",
                    "tool_name": "web_search",
                    "content": result,
                })

    cleanup()


if __name__ == "__main__":
    main()
