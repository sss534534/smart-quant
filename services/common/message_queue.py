import json
from typing import Any, Callable
from .redis_client import redis_client


class MessageQueue:
    def __init__(self, queue_name: str):
        self.queue_name = queue_name

    def publish(self, message: dict):
        redis_client.rpush(self.queue_name, json.dumps(message))

    def subscribe(self, callback: Callable):
        while True:
            result = redis_client.blpop(self.queue_name, timeout=5)
            if result:
                _, message = result
                callback(json.loads(message))

    def get_queue_length(self) -> int:
        return redis_client.llen(self.queue_name)


market_data_queue = MessageQueue("market_data")
trading_signal_queue = MessageQueue("trading_signal")
portfolio_update_queue = MessageQueue("portfolio_update")
