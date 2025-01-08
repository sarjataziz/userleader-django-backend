import requests
import os

# URL to your private Hugging Face model file
url = "https://huggingface.co/sarjat/best_rf_model/resolve/main/best_rf_model.pkl"

# Path to save the downloaded model
output_path = os.path.join(os.path.dirname(__file__), 'userleader_app', 'models', 'best_rf_model.pkl')

# Directly assign the token
hf_token = "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"

def download_file(url, output_path, token):
    """
    Downloads a file from a private Hugging Face repository.

    Parameters:
        url (str): The URL of the file to download.
        output_path (str): Local file path where the downloaded file will be saved.
        token (str): Hugging Face API token for authentication.
    """
    try:
        print(f"Downloading model from {url}...")
        # Add the authorization header
        headers = {"Authorization": f"Bearer {token}"}
        # Request the file from the URL
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()  # Raise HTTPError for bad responses
        # Save the file locally
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete!")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download the file: {e}")
        exit(1)

if __name__ == "__main__":
    if not os.path.exists(output_path):
        if not hf_token:
            print("Hugging Face API token not found.")
            exit(1)
        download_file(url, output_path, hf_token)
    else:
        print("Model file already exists.")
