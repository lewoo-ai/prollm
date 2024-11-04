# redis_handler.py
import redis
import os

# Redis 연결 설정
redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=os.getenv("REDIS_PORT", 6379),
    db=0,
    decode_responses=True
)

class RedisChatMemory:
    """Redis 기반의 채팅 기록 관리 클래스"""
    def __init__(self, session_id):
        self.session_id = session_id

    def save_context(self, human_input, output):
        """Redis에 사용자 입력과 응답을 저장"""
        redis_client.rpush(self.session_id, f"User: {human_input}")
        redis_client.rpush(self.session_id, f"LLM: {output}")

    def load_memory_variables(self):
        """Redis에서 채팅 기록을 불러오기"""
        history = redis_client.lrange(self.session_id, 0, -1)
        return {"history": history}

    def clear_memory(self):
        """채팅 기록 초기화"""
        redis_client.delete(self.session_id)
