import time
import requests

def benchmark_endpoint(url, num_requests=10):
    latencies = []
    print(f"Benchmarking: {url}")
    for i in range(num_requests):
        try:
            start_time = time.time()
            response = requests.get(url)
            latency = (time.time() - start_time) * 1000  # Convert to ms
            latencies.append(latency)
            if i % 2 == 0:
                print(f"  Request {i + 1}/{num_requests}: {response.status_code} ({latency:.2f} ms)")
        except requests.RequestException as e:
            print(f"  Request {i + 1} failed: {e}")
            break

    if latencies:
        avg = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        min_lat = min(latencies)
        print(f"Results for {url}:")
        print(f"  Avg Latency: {avg:.2f} ms")
        print(f"  Max Latency: {max_lat:.2f} ms")
        print(f"  Min Latency: {min_lat:.2f} ms\n")
    return latencies

if __name__ == "__main__":
    BASE_URL = "http://127.0.0.1:8000"
    endpoints = [
        f"{BASE_URL}/",         # Home page
        f"{BASE_URL}/shop/",      # Shop list
        f"{BASE_URL}/about/",     # About Us
    ]

    print("Starting Benchmarks...\n" + "="*30)
    for endpoint in endpoints:
        benchmark_endpoint(endpoint)
