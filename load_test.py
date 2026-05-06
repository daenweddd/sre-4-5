import requests
import time
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:8003/health"

TOTAL_REQUESTS = 1500
CONCURRENT_USERS = 100


def send_request(i):
    try:
        start = time.time()
        response = requests.get(URL, timeout=5)
        end = time.time()

        response_time = round(end - start, 4)

        print(f"Request {i} | Status: {response.status_code} | Time: {response_time}s")
        return response.status_code, response_time

    except Exception as error:
        print(f"Request {i} failed: {error}")
        return 500, 0


start_time = time.time()

with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
    results = list(executor.map(send_request, range(1, TOTAL_REQUESTS + 1)))

end_time = time.time()

successful = len([r for r in results if r[0] == 200])
failed = TOTAL_REQUESTS - successful
total_time = round(end_time - start_time, 2)
rps = round(TOTAL_REQUESTS / total_time, 2)
avg_response_time = round(sum(r[1] for r in results) / len(results), 4)

print("\nLoad Test Summary")
print(f"Total requests: {TOTAL_REQUESTS}")
print(f"Concurrent users: {CONCURRENT_USERS}")
print(f"Successful requests: {successful}")
print(f"Failed requests: {failed}")
print(f"Total time: {total_time}s")
print(f"Approximate RPS: {rps}")
print(f"Average response time: {avg_response_time}s")