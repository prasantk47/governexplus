import requests
import json

class InferenceClient:
    """Handles low-level communication with the inference API."""
    def __init__(self, api_key, endpoint):
        self.api_key = api_key
        self.endpoint = endpoint
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def post(self, payload):
        response = requests.post(
            self.endpoint,
            headers=self.headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        return response.json()

class InferenceModel:
    """Manages model state and high-level inference logic."""
    def __init__(self, model_id, api_key, endpoint):
        self.model_id = model_id
        self.client = InferenceClient(api_key, endpoint)

    def predict(self, input_data):
        payload = {
            "model_id": self.model_id,
            "inputs": input_data
        }
        return self.client.post(payload)

    def get_status(self):
        # Implementation for status check
        pass
