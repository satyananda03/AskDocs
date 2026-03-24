from typing import List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import json

class ChatHistoryRedis:
    def __init__(self, redis_instance, num_history: int, key_prefix: str = "aidocs"):
        self.redis = redis_instance.client 
        self.num_history = num_history       
        self.key_prefix = key_prefix 
        self.ttl = 86400 * 1 # 1 hari

    def get_history_key(self, session_id: str) -> str:
        return f"{self.key_prefix}:{session_id}:chat_history"
    
    async def save_history(self, session_id: str, question: str, answer: str) -> None:
        key = self.get_history_key(session_id)
        turn_data = {
            "question": question,
            "answer": answer,
        }
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.lpush(key, json.dumps(turn_data, ensure_ascii=False))
            # Trim berdasarkan max_storage
            # pipe.ltrim(key, 0, self.max_storage - 1) 
            pipe.expire(key, self.ttl)
            await pipe.execute()

    async def get_history_as_messages(self, session_id: str) -> List[BaseMessage]:
        key = self.get_history_key(session_id)
        # Ambil hanya n context terakhir 
        history_json = await self.redis.lrange(key, 0, self.num_history - 1)
        history_data = [json.loads(h) for h in history_json]
        history_data = list(reversed(history_data)) 
        messages = []
        for turn in history_data:
            messages.append(HumanMessage(content=turn['question']))
            messages.append(AIMessage(content=turn['answer']))
        return messages

    async def convert_to_messages(self, full_history: List[Dict]) -> List[BaseMessage]:
        # Ambil hanya n history turn terakhir
        recent_history = full_history[-self.num_history:] if full_history else []
        messages = []
        for turn in recent_history:
            messages.append(HumanMessage(content=turn['question']))
            messages.append(AIMessage(content=turn['answer']))
        return messages

    @staticmethod
    def get_history_as_string(history_messages: List[BaseMessage]) -> str:
        if not history_messages:
            return ""
        history = []
        for msg in history_messages:
            role = "HumanMessage" if isinstance(msg, HumanMessage) else "AIMessage"
            history.append(f"{role} : {msg.content.strip()}")
        return "\n".join(history)
    
    async def get_full_history(self, session_id: str) -> List[Dict]:
        key = self.get_history_key(session_id)
        history_json = await self.redis.lrange(key, 0, -1)
        history = [json.loads(h) for h in history_json]
        return list(reversed(history))