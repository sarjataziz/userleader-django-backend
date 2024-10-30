import gdown
import os

# Google Drive file ID for the model file
file_id = "1jFTayEKAzTltJkMeTNXgJcXi9-pbX4cZ"  
url = f"https://drive.google.com/uc?id={file_id}"
output_path = os.path.join(os.path.dirname(__file__), 'userleader_app', 'models', 'best_rf_model.pkl')

# Download the file if it doesn't exist
if not os.path.exists(output_path):
    print("Downloading model file...")
    gdown.download(url, output_path, quiet=False)
    print("Download complete!")
else:
    print("Model file already exists.")