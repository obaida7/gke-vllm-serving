# locustfile.py
# Advanced load testing script for LLM serving engines (vLLM / llama.cpp).
# Simulates streaming chat completions ("stream": true) and measures 
# client-side TTFT (Time-to-First-Token) and ITL (Inter-Token Latency).

import time
import json
import random
from locust import HttpUser, task, between, events

# Pool of retail shopper queries to simulate a live conversational shopping agent
SHOPPING_QUERIES = [
    "I need a summer dress for a beach wedding. What do you recommend?",
    "Do you have running shoes with good arch support under $100?",
    "What is your return policy for open-box electronics?",
    "Can you compare the features of the iPhone 15 and Samsung S24?",
    "I am looking for a waterproof backpack for hiking. It must fit a 15-inch laptop.",
    "Do these leather boots run true to size or should I size up?",
    "Suggest a skincare routine for sensitive, oily skin.",
    "Is the outdoor dining set made of weather-resistant teak wood?"
]

class LLMServingUser(HttpUser):
    # Simulated think-time between user inputs (1.5 to 3 seconds)
    wait_time = between(1.5, 3.0)

    @task
    def stream_chat_completion(self):
        prompt = random.choice(SHOPPING_QUERIES)
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "/mnt/models/Qwen2.5-0.5B-Instruct", # Matches model name in vLLM deployment
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 128,
            "temperature": 0.7,
            "stream": True # Enable SSE streaming
        }
        
        start_time = time.time()
        ttft = None
        itl_list = []
        last_token_time = None
        token_count = 0
        
        try:
            # Post request with stream=True
            with self.client.post("/v1/chat/completions", data=json.dumps(payload), headers=headers, stream=True, catch_response=True) as response:
                if response.status_code != 200:
                    response.failure(f"HTTP error {response.status_code}: {response.text}")
                    return
                
                # Iterate over the Server-Sent Events stream line by line
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8').strip()
                        if decoded_line.startswith("data:"):
                            event_time = time.time()
                            
                            # Standard SSE stream end token
                            if "[DONE]" in decoded_line:
                                break
                            
                            try:
                                # Clean data prefix and parse JSON
                                data_str = decoded_line[5:].strip()
                                data = json.loads(data_str)
                                
                                # Check if it contains generated tokens
                                choices = data.get("choices", [])
                                if choices and choices[0].get("delta", {}).get("content"):
                                    token_count += 1
                                    
                                    if ttft is None:
                                        # First token received: Calculate TTFT
                                        ttft = event_time - start_time
                                        last_token_time = event_time
                                    else:
                                        # Subsequent tokens: Calculate ITL
                                        itl = event_time - last_token_time
                                        itl_list.append(itl)
                                        last_token_time = event_time
                            except json.JSONDecodeError:
                                continue
                
                # Calculate final latency statistics
                total_duration = time.time() - start_time
                avg_itl = sum(itl_list) / len(itl_list) if itl_list else 0
                
                # Report custom metrics to Locust dashboard
                events.request.fire(
                    request_type="LLM_Stream",
                    name="Chat Completions (Streaming)",
                    response_time=total_duration * 1000, # Convert to ms
                    response_length=token_count,
                    exception=None
                )
                
                # Log detailed SLA statistics
                print(f"[METRICS] Tokens: {token_count} | TTFT: {ttft:.3f}s | Avg ITL: {avg_itl:.4f}s | Tokens/sec: {token_count/total_duration:.2f}")
                
        except Exception as e:
            events.request.fire(
                request_type="LLM_Stream",
                name="Chat Completions (Streaming)",
                response_time=0,
                response_length=0,
                exception=e
            )
            print(f"Request error: {e}")
