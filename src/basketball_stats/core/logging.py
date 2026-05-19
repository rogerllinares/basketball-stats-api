"""structlog config with tty-detected JSON / console renderer.

D-19: JSON for the Koyeb log aggregator (parseable); :class:`ConsoleRenderer` for
humans in dev. Detection: when ``ENV=prod`` or stdout is not a TTY, emit JSON.
``cache_logger_on_first_use=True`` freezes the processor chain after first use for perf.
"""

import logging
import sys

import structlog


def configure_logging(env: str = "dev", level: str = "INFO") -> None:
    """Configure structlog + stdlib logging once at startup.

    Args:
        env: ``prod`` forces JSON; anything else uses tty detection.
        level: stdlib log level (``DEBUG``/``INFO``/``WARNING``/...).
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    use_json = env.lower() == "prod" or not sys.stdout.isatty()
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if use_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
