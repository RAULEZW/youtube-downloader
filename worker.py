import redis
from rq import Worker, Queue

# Define Redis connection
import os
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
conn = redis.from_url(redis_url)

# Define the queue with the Redis connection
queue = Queue('default', connection=conn)

if __name__ == '__main__':
    worker = Worker([queue], connection=conn)
    worker.work()