"""日志初始化工具。"""

import logging


def configure_logging(debug: bool) -> None:
    # debug 模式下输出更详细的日志，方便本地排查问题；
    # 非 debug 模式下默认收敛到 INFO，避免日志过于嘈杂。
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
