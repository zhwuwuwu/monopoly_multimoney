"""Minimal CLI entry: delegates full logic to ContentSynchronizer."""
import argparse
import asyncio
from utils.logger import setup_logging, get_logger
from utils.config_loader import ConfigLoader
from core.synchronizer import ContentSynchronizer

logger = get_logger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Content generation pipeline")
    parser.add_argument("--config", default="config")
    parser.add_argument("--theme", required=True)
    parser.add_argument("--materials", required=True, help="Path to materials JSON file")
    parser.add_argument("--context", default="")
    parser.add_argument("--output")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--quality-threshold", type=float, default=0.0)
    args = parser.parse_args()

    config_loader = ConfigLoader(args.config)
    setup_logging(level=config_loader.get_config_value("LOG_LEVEL", "INFO"))

    sync = ContentSynchronizer(args.config)
    try:
        result = await sync.run_pipeline(
            theme=args.theme,
            materials_file=args.materials,
            additional_context=args.context,
            publish=args.publish,
            output=args.output,
            quality_threshold=args.quality_threshold,
        )
        content = result['content']
        print(f"标题: {content.title}\n字数: {content.word_count}\n标签: {', '.join(content.hashtags)}\n\n{content.content}")
    finally:
        await sync.shutdown()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())