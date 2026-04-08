import requests
import json

def discover():
    try:
        url = "http://localhost:7860/openapi.json"
        print(f"Fetching schema from {url}...")
        response = requests.get(url)
        if response.status_code == 200:
            schema = response.json()
            print("Successfully fetched OpenAPI schema.")
            
            # Look at /step endpoint
            paths = schema.get("paths", {})
            step_path = paths.get("/step", {})
            post_method = step_path.get("post", {})
            request_body = post_method.get("requestBody", {})
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            schema_ref = json_content.get("schema", {})
            
            print(f"\n[/step] Request Body Schema: {json.dumps(schema_ref, indent=2)}")
            
            # Resolve refs if any
            components = schema.get("components", {}).get("schemas", {})
            print("\n[Components] Schemas:")
            for name, details in components.items():
                print(f"\n--- {name} ---")
                print(json.dumps(details, indent=2))
        else:
            print(f"Failed to fetch schema: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    discover()
