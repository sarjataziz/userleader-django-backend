import requests
import os

url = "https://huggingface.co/sarjat/best_rf_model/resolve/main/best_rf_model.pkl"
output_path = os.path.join(os.path.dirname(__file__), 'userleader_app', 'models', 'best_rf_model.pkl')

def download_file(url, output_path):
    try:
        print(f"Downloading model from {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete!")
    except Exception as e:
        print(f"Failed to download the file: {e}")
        exit(1)

if not os.path.exists(output_path):
    download_file(url, output_path)
else:
    print("Model file already exists.")

